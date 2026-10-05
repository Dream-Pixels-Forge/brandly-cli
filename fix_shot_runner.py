import re

s = open("src/brandly_cli/shot_runner.py", "r", encoding="utf-8").read()
s = re.sub(
    r"config\.move_shot_clips\(logical, name_clips\(logical, new_clips, config\.say\)\)\s*_fire_hook\(config, logical, True\)\s*return True, exit_code, note",
    """config.move_shot_clips(logical, name_clips(logical, new_clips, config.say))
                        # G8: Measure clip duration and check for continuation
                        primary_clip = new_clips[0] if new_clips else None
                        if primary_clip and primary_clip.exists():
                            from brandly_cli.shot_runner import _probe_video_duration, needs_continuation, MAX_CONTINUATION_ATTEMPTS
                            measured_s = _probe_video_duration(primary_clip)
                            requested_s = logical.duration
                            if measured_s is not None:
                                logical.measured_s = measured_s
                                logical.requested_s = requested_s
                                logical.delta_s = round(measured_s - requested_s, 2)
                                logical.duration_status = duration_status(requested_s, measured_s)
                                config.say(f"  Duration: requested={requested_s}s, measured={measured_s:.2f}s ({logical.duration_status})")
                                
                                # G8: Generate continuation if needed
                                if needs_continuation(requested_s, measured_s):
                                    measured_s, attempts = _generate_continuation(
                                        config=config,
                                        logical=logical,
                                        scenes_dir=scenes_dir,
                                        scenes=scenes,
                                        _clip_snapshot=_clip_snapshot,
                                        name_clips=name_clips,
                                        config_move_shot_clips=config.move_shot_clips,
                                        current_clip=primary_clip,
                                        measured_s=measured_s,
                                        requested_s=requested_s,
                                    )
                                    # Update final measured duration after continuations
                                    logical.measured_s = measured_s
                                    logical.delta_s = round(measured_s - requested_s, 2)
                                    logical.duration_status = duration_status(requested_s, measured_s)
                        
                        _fire_hook(config, logical, True)
                        return True, exit_code, note""",
    s,
    flags=re.DOTALL
)
open("src/brandly_cli/shot_runner.py", "w", encoding="utf-8").write(s)
print("Fixed")