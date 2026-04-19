# Use the official LiveKit Server image as the base
FROM livekit/livekit-server:latest

# Expose the ports LiveKit needs to communicate:
# 7880: HTTP (API & WebRTC signaling)
# 7881: TCP (WebRTC fallback)
# 7882/udp: UDP (WebRTC media routing)
EXPOSE 7880 7881 7882/udp

# Start the server in development mode.
# This automatically binds the server to local interfaces and 
# sets the API Key to "devkey" and the Secret to "secret".
CMD ["--dev"]