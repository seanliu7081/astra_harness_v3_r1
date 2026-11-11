"""One CPU-only vertical slice. No live model, weights, simulator or task run."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import numpy as np

from gpt_field.action import TRANSLATION_SCALE_M
from gpt_field.agent_speedup_v2_sim import initial_observation_sha256
from gpt_field.agent_speedup_v2_user_check_sim import CalibratedObservation
from gpt_field.foundation_vision.types import Detection
from gpt_field.foundation_vision_harness_V3.client import FoundationVisionHarnessClient
from gpt_field.foundation_vision_harness_V3 import executor
from gpt_field.foundation_vision_harness_V3.runner import execute_episode
from gpt_field.foundation_vision_harness_V3.vision_tools import OnDemandVisionTools
from gpt_field.observation import image_to_data_url
from test_foundation_vision_bridge import metadata


def test_complete_optional_vision_framework(tmp_path, monkeypatch):
    class Clock:
        now = 1000.
        def __call__(self): return self.now
    clock = Clock()
    monkeypatch.setattr(executor, "monotonic", clock)
    from gpt_field.foundation_vision_harness_V3 import REVISION
    assert REVISION == "astra_tools_r1"

    task = SimpleNamespace(key="fixture", task_id=4, prompt="Move and inspect the selected object.")
    state = (0., 0., .2, 0., 0., 0., .04, -.04)
    url = image_to_data_url(np.zeros((512, 512, 3), np.uint8), size=512, rotate=False)
    initial = CalibratedObservation(url, url, state, task.prompt, (0.,)*7, (0.,)*7,
                                    geometry=metadata(list(state), 512))

    class Simulator:
        config = SimpleNamespace(stop_on_success=False)
        metadata = {"oracle_enabled": False}
        def __init__(self):
            self.current = initial
            self.actions = []
            self.status = {"libero_success": False, "terminated": False}
        def start(self): pass
        def list_tasks(self): return [{"task_id": 4, "prompt": task.prompt}]
        def reset(self, task_id, episode_index): return self.current
        def step(self, action):
            self.actions.append(tuple(action))
            assert len(self.actions) < 180, "offline fixture did not make progress"
            clock.now += .05
            values = np.asarray(self.current.state).copy()
            values[:3] += np.asarray(action[:3])*TRANSLATION_SCALE_M
            values[6:8] = [.012, -.012] if action[6] > 0 else [.04, -.04]
            self.current = replace(self.current, state=tuple(values), geometry=metadata(values.tolist(), 512))
            # Evaluator success must never stop the policy or reach its context.
            self.status["libero_success"] = True
            return self.current, True
        def truth(self):
            return {"strict_conjunction": False, "check_success": True, "atoms": []}
        def close(self): pass

    class Guard:
        def __init__(self): self.issued, self.acknowledged = [], []
        def filter(self, action, view, segment):
            actual = list(action)
            if not self.issued:
                actual[:3] = [v*.5 for v in actual[:3]]
            self.issued.append(tuple(actual))
            return {"status": "scaled", "action": actual, "evidence": {"fixture": True}}
        def observe_transition(self, before, actual, after): self.acknowledged.append(tuple(actual))
        def stats(self): return {"calls": len(self.issued)}

    loads = []
    class Segmenter:
        def segment(self, frame, targets):
            # A usable mask becomes stale while the backend is loading/running.
            clock.now += 61.
            return [Detection(camera.name, target.key, np.ones(camera.rgb.shape[:2], bool), .9)
                    for target in targets for camera in frame.cameras]
    def backend():
        loads.append(True)
        return SimpleNamespace(segmenter=Segmenter())
    tools = OnDemandVisionTools(engine_factory=backend, clock=clock, max_age_s=60.,
                                output_dir=tmp_path/"trial"/"tools")
    assert not (tmp_path/"trial").exists()
    assert not loads and tools.stats()["calls"] == 0
    guard, sim = Guard(), Simulator()
    box = {"lower_xyz_m": [.015, -.003, .195], "upper_xyz_m": [.025, .003, .205]}
    stationary = {"lower_xyz_m": [.01, .06, .19], "upper_xyz_m": [.03, .08, .22]}
    relocated = {"lower_xyz_m": [-.06, -.003, .195], "upper_xyz_m": [-.05, .003, .205]}

    def motion(delta, profile="contact", checkpoint=None):
        return {"object": "selected object", "checkpoint": checkpoint,
                "candidates": [{"skill": "move_relative", "xyz_m": delta,
                                "quaternion_wxyz": None, "profile": profile}]}
    def response(status, segments=(), measurements=(), obstacle_map=None):
        return {"status": status, "why": "Synthetic public-feedback fixture.",
                "segments": list(segments), "measurements": list(measurements), "obstacle_map": obstacle_map}

    class Transport:
        offline_mock = True
        def __init__(self): self.contexts = []
        def __call__(self, endpoint, payload, headers, timeout_s):
            fields = json.loads(payload["input"][-1]["content"][0]["text"])
            context = fields["context"]
            self.contexts.append(deepcopy(context))
            clock.now += 20.  # Model latency must remain part of source-frame age.
            index = len(self.contexts)
            if index == 1:
                assert not loads
                assert context["obstacle_map"]["source"] == "uninitialized"
                assert context["obstacle_map"]["revision"] == 0
                answer = response("execute", [motion([.04, 0., 0.], "transit"),
                    motion([0., .008, 0.]),
                    {"object": "selected object", "checkpoint": None, "candidates": [{"skill": "close"}]},
                    motion([0., 0., .01], checkpoint={"state": "held", "object": "selected object"})],
                    obstacle_map={"avoid_boxes": [box, stationary], "clearance_m": .001})
            elif index == 2:
                assert context["feedback"]["reason"] == "visual_checkpoint"
                assert len(context["segment_history"]) == 4
                assert not loads  # The whole first batch needed no visual model.
                assert context["obstacle_map"]["revision"] == 1
                assert context["obstacle_map"]["updated_at_step"] == 0
                answer = response("measure", measurements=[{"id": "handle", "kind": "segment",
                    "query": "handle", "view": "external", "region": None, "pixel": None}])
            elif index == 3:
                tool = context["tool_results"][-1]
                assert tool["results"][0]["reason"] == "observation_expired"
                assert tool["age_s"] >= 81.  # Includes previous model wait, not restamped.
                assert context["obstacle_map"] == self.contexts[1]["obstacle_map"]
                answer = response("execute", [motion([.006, 0., 0.], "transit")])
            elif index == 4:
                assert context["feedback"]["reason"] == "batch_complete"
                # null reused both geometry and its original update step.
                assert context["obstacle_map"] == self.contexts[1]["obstacle_map"]
                # Replace a moved object's box while retaining a stationary one.
                answer = response("execute", [motion([.012, 0., 0.], "transit")],
                    obstacle_map={"avoid_boxes": [stationary, relocated], "clearance_m": .001})
            else:
                assert index == 5
                assert context["feedback"]["reason"] == "batch_complete"
                assert context["obstacle_map"]["avoid_boxes"] == [stationary, relocated]
                assert context["obstacle_map"]["revision"] == 2
                assert context["obstacle_map"]["updated_at_step"] == self.contexts[3]["step"]
                answer = response("finish")
            return {"id": f"fixture-{index}", "status": "completed", "model": payload["model"],
                "reasoning": {"effort": "high"}, "offline_mock": True,
                "output": [{"type": "message", "role": "assistant", "status": "completed",
                            "content": [{"type": "output_text", "text": json.dumps(answer)}]}],
                "usage": {"input_tokens": 0, "output_tokens": 5,
                          "output_tokens_details": {"reasoning_tokens": 2}}}

    transport = Transport()
    client = FoundationVisionHarnessClient(task_prompt=task.prompt, transport=transport)
    policy = executor.FoundationVisionHarnessPolicy(client, vision_tools=tools, robot_guard=guard,
                                                    output_dir=tmp_path/"events")
    result = execute_episode(tmp_path/"trial", task=task, episode_index=0,
        sim_factory=lambda: sim, client_factory=lambda **kwargs: client,
        policy_factory=lambda supplied: policy, clock=clock,
        expected_initial_observation_sha256=initial_observation_sha256(initial.to_dict()))
    assert result["status"] == "finish", result["error"]
    assert result["version"] == "foundation_vision_harness_V3"
    assert not result["strict_success"]  # A model finish is not evaluator success.
    assert len(transport.contexts) == 5 and policy.completed_segments == 6
    assert loads == [True] and tools.stats()["calls"] == 1
    assert guard.issued == guard.acknowledged
    np.testing.assert_allclose(sim.current.state[:3], [.058, .008, .21], atol=.004)
    assert all(action[6] > 0 for action in sim.actions[-10:])  # No implicit release.
    assert result["same_gripper_hold_steps"] == 10
    first = policy.history[0]["evidence"]["segments"][0]["routing"]
    assert first["map_source"] == "shared_map" and first["obstacle_count"] == 2
    assert first["straight_path_valid"] is False  # The Astra box really affects routing.
    events = [json.loads(line) for line in (tmp_path/"events/events.jsonl").read_text().splitlines()]
    routed = next(event for event in events if event["event"] == "segment_result")
    assert routed["outcome"]["evidence"]["segments"][0]["routing"]["grid"]["spacing_m"] == .02
    assert routed["outcome"]["evidence"]["budget_steps"] == 120
    assert policy.planning_snapshot()["obstacle_boxes"] == [stationary, relocated]
    assert not result["cleanup_errors"]


def test_r1_keeps_bounded_fragments_and_requires_complete_valid_batches():
    """Later revisions must not silently replace the archived r1 protocol."""
    import pytest
    from gpt_field.foundation_vision_harness_V3.protocol import (
        ProtocolRepairError, validate_contract,
    )

    def move(profile):
        return {"object": "selected object", "checkpoint": None,
                "candidates": [{"skill": "move_relative", "xyz_m": [.04, 0., 0.],
                                "quaternion_wxyz": None, "profile": profile}]}

    proposal = {"status": "execute", "why": "Synthetic two-stage batch.",
                "segments": [move("transit"), move("contact")],
                "measurements": [], "obstacle_map": None}
    normalized = validate_contract(proposal)
    assert [s["candidates"][0]["max_steps"] for s in normalized["segments"]] == [120, 80]
    assert "max_steps" not in proposal["segments"][0]["candidates"][0]

    # An invalid later stage rejects the whole batch before a valid prefix runs.
    proposal["segments"][1]["candidates"][0]["xyz_m"] = [float("nan"), 0., 0.]
    with pytest.raises(ProtocolRepairError) as caught:
        validate_contract(proposal)
    assert caught.value.evidence["no_candidate_executed"] is True


def test_vision_off_never_loads_a_backend():
    def unexpected_load():
        raise AssertionError("disabled optional vision tried to initialize")

    tools = OnDemandVisionTools(mode="off", engine_factory=unexpected_load)
    assert tools.capabilities()["enabled"] is False
    assert tools.capabilities()["sam"] == "disabled"
    assert tools.capabilities()["da3"] == "disabled"
    assert tools.stats()["factory_calls"] == 0
    assert tools.stats()["automatic_calls"] == 0
