#!/usr/bin/env bash

# Clean up after test suite
clean() {
  data/test.db proposal.json investor.json proposal_archive.json investor_archive.json 2> /dev/null
}

if [ "$CRC_BANK_TEST" = 'true' ]; then
    #sudo sacctmgr -i modify account where account=sam cluster=smp,gpu,mpi,htc set rawusage=0
    for bat in $(ls tests/*.bats); do
        echo "====== BEGIN $bat ======"
        bats $bat
        if [ $? -ne 0 ]; then
            clean
            exit
        fi
        echo "======  END $bat  ======"
    done
else
    echo "$CRC_BANK_TEST must be set to 'true' in working env to run tests."
    echo "This is to protect accidental overwrite of the operational database."
fi

clean