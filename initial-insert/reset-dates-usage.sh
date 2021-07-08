#!/usr/bin/env bash

home_dir=/ihome/crc/bank
crc_bank=$home_dir/crc-bank.py
cron_logs=$home_dir/logs/cron.log

# generate a list of all of the accounts
accounts=($(sacctmgr list accounts -n format=account%30))

for i in ${accounts[@]}; do
    $crc_bank reset_usage $i
done
