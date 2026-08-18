#!/usr/bin/env python3
"""Unit tests for 让文本模型拥有多模态的技能 model fallback logic + official V2.0 video format."""
import sys, importlib.util

spec = importlib.util.spec_from_file_location("agnes_api", "scripts/agnes_api.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Args:
    prompt = "A cinematic shot of a cat walking on the beach at sunset"
    mode = "text"
    seconds = 5
    aspect_ratio = None
    seed = None
    negative_prompt = None
    images = None
    first_frame = None
    last_frame = None
    model = None


def test_video_text_payload():
    """Official text-to-video: model + prompt + width/height + num_frames + frame_rate"""
    p = m._build_video_payload(Args())
    assert p["model"] == "agnes-video-v2.0", p
    assert p["width"] == 1152 and p["height"] == 768, p  # official defaults
    assert p["num_frames"] == 121, p  # 5s -> 8n+1
    assert p["frame_rate"] == 24
    assert "extra_body" not in p
    print("PASS text payload:", p)


def test_video_image_to_video():
    """Official image-to-video: `image` field (single URL)"""
    Args.images = "https://example.com/photo.png"
    p = m._build_video_payload(Args())
    assert p["image"] == "https://example.com/photo.png", p
    print("PASS image-to-video payload:", p)


def test_video_keyframe_payload():
    """Official keyframes: extra_body.image array + extra_body.mode = keyframes"""
    Args.mode = "keyframe"
    Args.first_frame = "https://example.com/kf1.png"
    Args.last_frame = "https://example.com/kf2.png"
    Args.images = None
    p = m._build_video_payload(Args())
    assert p["extra_body"]["mode"] == "keyframes", p
    assert p["extra_body"]["image"] == [
        "https://example.com/kf1.png", "https://example.com/kf2.png"], p
    print("PASS keyframe payload:", p)


def test_video_aspect_ratio():
    Args.mode = "text"
    Args.aspect_ratio = "9:16"
    p = m._build_video_payload(Args())
    assert p["width"] == 720 and p["height"] == 1280, p
    Args.aspect_ratio = None
    print("PASS aspect_ratio mapping")


def test_video_negative_prompt():
    Args.negative_prompt = "blurry, low quality"
    p = m._build_video_payload(Args())
    assert p["negative_prompt"] == "blurry, low quality", p
    Args.negative_prompt = None
    print("PASS negative_prompt")


def test_video_id_extraction():
    r = {"id": "task_1", "task_id": "task_1", "video_id": "video_abc"}
    assert m._get_video_id(r) == "video_abc"  # prefers video_id (official)
    r2 = {"id": "task_2"}
    assert m._get_video_id(r2) == "task_2"
    print("PASS video_id extraction")


def test_video_status_url():
    url = m._video_status_url("video_abc")
    assert url == "https://apihub.agnes-ai.com/agnesapi?video_id=video_abc", url
    print("PASS status url:", url)


def test_video_url_extraction():
    # Official: metadata.url on completion
    r = {"status": "completed", "metadata": {"url": "https://x.com/v.mp4"}}
    assert m._extract_video_url(r) == "https://x.com/v.mp4"
    print("PASS video url extraction")


def test_num_frames_bounds():
    assert m._num_frames_for_seconds(4) == 97
    assert m._num_frames_for_seconds(12) == 289
    assert m._num_frames_for_seconds(20) == 441  # capped
    print("PASS num_frames bounds")


def test_model_error_detection():
    e_model = m.APIError(400, {"error": "model not found"})
    e_param = m.APIError(400, {"error": "prompt too long"})
    e_500 = m.APIError(500, {"error": "boom"})
    e_401 = m.APIError(401, {"error": "unauthorized"})
    e_404 = m.APIError(404, {"error": "no such model"})
    assert m._is_model_error(e_model) is True
    assert m._is_model_error(e_param) is False
    assert m._is_model_error(e_500) is True
    assert m._is_model_error(e_401) is False
    assert m._is_model_error(e_404) is True
    print("PASS model error detection")


def test_model_lists():
    # Video should only contain official v2.0 by default
    assert m.MODELS_VIDEO == ["agnes-video-v2.0"]
    assert m.MODEL_VIDEO == "agnes-video-v2.0"
    assert m.MODELS_IMAGE == ["agnes-image-2.1-flash", "agnes-image-2.0-flash"]
    assert m.MODELS_VISION == ["agnes-2.0-flash", "agnes-1.5-flash"]
    print("PASS model lists")


if __name__ == "__main__":
    test_video_text_payload()
    test_video_image_to_video()
    test_video_keyframe_payload()
    test_video_aspect_ratio()
    test_video_negative_prompt()
    test_video_id_extraction()
    test_video_status_url()
    test_video_url_extraction()
    test_num_frames_bounds()
    test_model_error_detection()
    test_model_lists()
    print("\nALL TESTS PASSED")
