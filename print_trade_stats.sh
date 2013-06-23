#!/bin/bash

# Compute stats for generated and actual trades: 
python print_trade_stats_gen.py events.log.gz 
python print_trade_stats_orig.py AXISBANK-trades.csv `zcat events.log.gz | tail -2 | cut -d',' -f1| head -1`

echo 'Time of last generated event: ' `zcat events.log.gz | tail -2 | cut -d',' -f1 | head -1`

echo 'Total generated events:       ' `zcat events.log.gz | cut -d',' -f5 | wc -l`
