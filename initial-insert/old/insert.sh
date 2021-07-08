#!/usr/bin/env bash

while read line; do
    echo $line
    sp=($(echo $line))
    account=${sp[0]}
    sus=${sp[1]}
    ../crc-bank.py insert $account $sus
done < data.txt
