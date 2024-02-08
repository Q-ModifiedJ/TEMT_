#!/usr/bin/env bash
PID="$(jps | grep Benchmark | awk '{print $1}')"
kill -9 $PID 1 > /dev/null 2>&1
echo "Nexmark processes has been cleared."