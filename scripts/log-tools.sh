#!/bin/sh
/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker logs openclaw --since 5m 2>&1 | grep 'embedded run tool' | tail -20 >> /share/CACHEDEV1_DATA/docker/ai-agent/logs/tool_calls.log