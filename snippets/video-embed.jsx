/*
 * VideoEmbed — click-to-play YouTube player with a custom poster image.
 *
 * Mintlify counterpart of the Hugo `video_embed` shortcode
 * (docs/themes/kinetica/layouts/shortcodes/video_embed.html).  The Hugo
 * version shows a branded thumbnail with a play-button overlay and only
 * loads the YouTube iframe once the reader clicks; this does the same,
 * swapping the poster for the iframe in place instead of opening a modal.
 *
 * Emitted by convert_video_shortcode() in mintlify/convert_content.py and
 * installed to <mintlify-root>/snippets/ by mintlify/copy_assets.sh.  Pages
 * that use it get an `import { VideoEmbed } from "/snippets/video-embed.jsx"`
 * line injected below their front matter — Mintlify requires every page to
 * import the components it renders.
 *
 * Notes:
 *   - React hooks are pre-injected by Mintlify; do NOT import from "react".
 *   - The poster JPEGs are YouTube hqdefault stills: 480x360 with black
 *     letterbox bars.  A 16:9 box plus objectFit:"cover" crops the bars and
 *     keeps the poster and the iframe exactly the same size, so clicking
 *     play causes no layout shift.
 *   - Styling is inline so the component stays self-contained; the caption
 *     uses currentColor/opacity so it reads correctly in light and dark mode.
 */

export const VideoEmbed = ({ id, thumb, title, caption, maxWidth }) => {
  const [playing, setPlaying] = useState(false);
  const [hover, setHover] = useState(false);

  const label = title ? `Play video: ${title}` : "Play video";

  return (
    <div style={{ maxWidth: maxWidth || "480px", margin: "1.5rem 0" }}>
      <div
        style={{
          position: "relative",
          width: "100%",
          aspectRatio: "16 / 9",
          borderRadius: "8px",
          overflow: "hidden",
          background: "#000",
        }}
      >
        {playing ? (
          <iframe
            src={`https://www.youtube.com/embed/${id}?autoplay=1&rel=0`}
            title={title || "Video"}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              border: 0,
            }}
          />
        ) : (
          <button
            type="button"
            aria-label={label}
            onClick={() => setPlaying(true)}
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
            onFocus={() => setHover(true)}
            onBlur={() => setHover(false)}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              padding: 0,
              border: 0,
              background: "none",
              cursor: "pointer",
              display: "block",
            }}
          >
            <img
              src={thumb}
              alt={title || ""}
              loading="lazy"
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                display: "block",
                margin: 0,
                borderRadius: 0,
              }}
            />
            <span
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <svg
                width="64"
                height="64"
                viewBox="0 0 32 32"
                aria-hidden="true"
                style={{
                  opacity: hover ? 1 : 0.82,
                  transform: hover ? "scale(1.06)" : "scale(1)",
                  transition: "opacity .15s ease, transform .15s ease",
                  filter: "drop-shadow(0 2px 4px rgba(0,0,0,.45))",
                }}
              >
                <path
                  fill="#ffffff"
                  d="M16 0C7.164 0 0 7.164 0 16s7.164 16 16 16 16-7.164 16-16S24.836 0 16 0zm-6 24V8l16.008 8L10 24z"
                />
              </svg>
            </span>
          </button>
        )}
      </div>
      {(title || caption) && (
        <div style={{ marginTop: ".5rem", lineHeight: 1.35 }}>
          {title && <div style={{ fontWeight: 600 }}>{title}</div>}
          {caption && (
            <div style={{ fontSize: ".875em", opacity: 0.7 }}>{caption}</div>
          )}
        </div>
      )}
    </div>
  );
};
