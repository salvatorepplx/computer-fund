#!/bin/bash
# Capture-tick trigger: always fire (exit 0). The capture should run every scheduled tick to
# build the sentiment series; de-bursting (>180s spacing) is handled downstream in leadlag_real.py.
# This trigger exists only to unlock sub-hourly cadence; it does no gating.
exit 0
