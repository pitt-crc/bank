#!/usr/bin/env bash

# Set up directories and specify an admin to email details to
home_dir=/ihome/crc/bank
crc_bank=$home_dir/crc_bank.py
cron_logs=$home_dir/logs/cron.log
admin_email=nlc60@pitt.edu

# Generate a list of all of the accounts
accounts=($(sacctmgr list accounts -n -P format=account))

# Initialize list of accounts that are over the SU limit or expired 
over_limit=
expired=

for acc in ${accounts[@]}; do
    $crc_bank info $acc &> /dev/null
    if [ $? -ne 0 ]; then
        mail -s "crc_bank.py error: no account for $acc" $admin_email <<< "Unable to find an account for $acc"
    else
        $crc_bank check_sus_limit $acc >> $cron_logs 2>&1
        $crc_bank check_proposal_end_date $acc >> $cron_logs 2>&1
    fi
done

dateVar=`date +"%Y-%m-%d"` 
cat /ihome/crc/bank/logs/crc_bank.log | grep ${dateVar} | grep locked | mail -s "${dateVar} Locked Accounts" $admin_email 



