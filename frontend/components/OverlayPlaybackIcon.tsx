export default function OverlayPlaybackIcon({
  state,
  size = 40,
}: {
  state: "play" | "pause";
  size?: number;
}) {
  return (
    <svg
      className="overlay-playback-icon"
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="24" cy="24" r="24" fill="black" fillOpacity="0.5" />
      {state === "play" ? (
        <path d="M20 15.5 34 24 20 32.5Z" fill="white" />
      ) : (
        <>
          <rect x="17.5" y="15" width="5" height="18" rx="2" fill="white" />
          <rect x="25.5" y="15" width="5" height="18" rx="2" fill="white" />
        </>
      )}
    </svg>
  );
}
