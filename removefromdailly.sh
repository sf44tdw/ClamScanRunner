#!/bin/bash

source ./pathes

ls -l "${DAILY_DEST}" "${ROCKFILE_ERASER_SCRIPT_DEST}" "${ROCKFILE_ERASER_DEST}"
echo
rm -f "${DAILY_DEST}" "${ROCKFILE_ERASER_SCRIPT_DEST}" "${ROCKFILE_ERASER_DEST}"
echo
ls -l "${DAILY_DEST}" "${ROCKFILE_ERASER_SCRIPT_DEST}" "${ROCKFILE_ERASER_DEST}"
