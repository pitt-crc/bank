#!/usr/bin/env /ihome/crc/install/python/miniconda3-3.7/bin/python

import dataset
import pandas as pd

import utils

CLUSTERS = ["smp", "mpi", "gpu", "htc"]

old_db = dataset.connect("sqlite:////ihome/crc/bank-old-8-11-20/old/crc-bank.db")
db = dataset.connect("sqlite:///crc_bank.db")

entries = list(old_db["crc"].find())
entries_len = len(entries)

df = pd.read_csv("./migration_helper.csv")

for idx, entry in enumerate(entries):
    try:
        row = df[df["Account"] == entry["account"]].iloc[0]
    except IndexError:
        print(entry["account"])

    build_dict = {
        "start_date": entry["date"],
        "smp": int(row["SMP"]),
        "mpi": int(row["MPI"]),
        "gpu": int(row["GPU"]),
        "htc": int(row["HTC"]),
        "account": entry["account"]
    }

    # Determine percent_notified currently
    used_sus_per_cluster = {c: 0 for c in CLUSTERS}
    for cluster in CLUSTERS:
        used_sus_per_cluster[cluster] = utils.get_raw_usage_in_hours(
            build_dict["account"], cluster
        )
    total_sus = entry["su_limit_hrs"]
    used_sus = sum(used_sus_per_cluster.values())
    percent_usage = 100.0 * used_sus / total_sus
    updated_notification_percent = utils.find_next_notification(percent_usage)
    build_dict["percent_notified"] = updated_notification_percent.value

    # Determine proposal_type
    if entry["account"].isalpha():
        proposal_type = utils.unwrap_if_right(utils.parse_proposal_type("proposal"))
    else:
        proposal_type = utils.unwrap_if_right(utils.parse_proposal_type("class"))
    build_dict["proposal_type"] = proposal_type.value
    proposal_duration = utils.get_proposal_duration(proposal_type)
    build_dict["end_date"] = build_dict["start_date"] + proposal_duration

    db["proposal"].insert(build_dict)

    if idx % 10 == 0:
        print(f"{idx}/{entries_len}")
