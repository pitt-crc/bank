#!/usr/bin/env bash

rm test.db proposal.json investor.json proposal_archive.json investor_archive.json

if [ $CRC_TEST = 'true' ]; then
    sudo sacctmgr -i modify account where account=sam cluster=smp,gpu,mpi,htc set rawusage=0
    for bat in $(ls tests/*.bats); do
        echo "====== BEGIN $bat ======"
        bats $bat
        if [ $? -ne 0 ]; then
            exit
        fi
        echo "======  END $bat  ======"
    done
else
    echo "CRC_TEST must be set to `true` in working env to run tests."
    echo "This is to protect accidental overwrite of the operational database."
fi
