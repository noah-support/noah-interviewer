# Self-hosted LiveKit server (local/staging). For production WebRTC, prefer LiveKit Cloud.
FROM livekit/livekit-server:latest

EXPOSE 7880 7881 7882/udp

# Dev credentials: API key "devkey", secret "secret".
# Production: mount a config file and remove --dev (see docs/DEPLOYMENT.md).
CMD ["--dev"]
