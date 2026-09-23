import { useRef, useCallback, useEffect } from 'react';
import { useAppStore } from '../store';

export interface PlaybackState {
  play: () => void;
  pause: () => void;
  stop: () => void;
  seekToFrame: (frame: number) => void;
  isPlaying: boolean;
  currentTime: number;
}

export function usePlayback(): PlaybackState {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const { isPlaying, currentFrame, totalFrames, playbackRate, setPlayhead, togglePlay } = useAppStore();

  const timeToFrame = useCallback(
    (time: number) => Math.round((time / (videoRef.current?.duration ?? 1)) * totalFrames),
    [totalFrames],
  );

  const seekToFrame = useCallback(
    (frame: number) => {
      const clamped = Math.max(0, Math.min(frame, totalFrames));
      setPlayhead(clamped);
      if (videoRef.current) {
        const t = (clamped / (totalFrames || 1)) * (videoRef.current.duration || 0);
        videoRef.current.currentTime = t;
      }
    },
    [totalFrames, setPlayhead],
  );

  const play = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.play().catch(() => {});
    }
    togglePlay();
  }, [togglePlay]);

  const pause = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.pause();
    }
    togglePlay();
  }, [togglePlay]);

  const stop = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
    setPlayhead(0);
    togglePlay();
  }, [setPlayhead, togglePlay]);

  const onVideoEnded = useCallback(() => {
    const { loop, currentFrame: cf, totalFrames: tf } = useAppStore.getState();
    if (loop) {
      seekToFrame(0);
      play();
    } else if (cf >= tf - 1) {
      pause();
    } else {
      seekToFrame(cf + 1);
    }
  }, [seekToFrame, play, pause]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onTimeUpdate = () => {
      const frame = timeToFrame(video.currentTime);
      setPlayhead(frame);
    };

    const onPlay = () => useAppStore.setState({ isPlaying: true });
    const onPause = () => useAppStore.setState({ isPlaying: false });
    const onEnded = onVideoEnded;

    video.addEventListener('timeupdate', onTimeUpdate);
    video.addEventListener('play', onPlay);
    video.addEventListener('pause', onPause);
    video.addEventListener('ended', onEnded);

    return () => {
      video.removeEventListener('timeupdate', onTimeUpdate);
      video.removeEventListener('play', onPlay);
      video.removeEventListener('pause', onPause);
      video.removeEventListener('ended', onEnded);
    };
  }, [timeToFrame, setPlayhead, onVideoEnded]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    video.playbackRate = playbackRate;
  }, [playbackRate]);

  const currentTime = currentFrame / (totalFrames > 0 ? 24 : 1);

  return { play, pause, stop, seekToFrame, isPlaying, currentTime };
}
