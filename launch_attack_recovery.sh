#!/bin/bash

tmux kill-session -t "geck_demo_recovery_part"

# Name of the tmux session
SESSION_NAME="geck_demo_recovery_part"

# Step 1: Create a new tmux session with the first window in detached mode
tmux new-session -d -s "$SESSION_NAME" -n "window1"

# Check if the session was created successfully
if [ $? -eq 0 ]; then
    echo "Tmux session '$SESSION_NAME' created successfully."
else
    echo "Failed to create tmux session '$SESSION_NAME'."
    exit 1
fi

tmux split-window -h -t "$SESSION_NAME:0"

# Send the commands to the tmux session
COMMANDS_WINDOW1=(
    "cp gps_data.txt /tmp/"
    "pkill arducopter"
    "sudo ~/Gecko/checkpoint_restore/criu/criu restore -D /mnt/ramdisk --shell-job"
    "0"
)

for CMD in "${COMMANDS_WINDOW1[@]}"; do
    tmux send-keys -t "$SESSION_NAME:0.0" "$CMD" C-m
    sleep 0.5
done

sleep 1

# COMMANDS_WINDOW2=(
#     "mavproxy.py --master tcp:127.0.0.1:5760 --map --console"
# )

# for CMD in "${COMMANDS_WINDOW2[@]}"; do
#     tmux send-keys -t "$SESSION_NAME:0.1" "$CMD" C-m
# done

echo "Attaching to tmux session '$SESSION_NAME'..."
tmux attach-session -t "$SESSION_NAME"
