#!/bin/bash

# Compute stats for generated and actual trades: 
python print_trade_stats_gen.py events.log 
python print_trade_stats_orig.py AXISBANK-trades.csv `tail -2 events.log | cut -d',' -f1| head -1`

echo 'Time of last generated event: ' `tail -2 events.log | cut -d',' -f1 | head -1`

echo 'Total generated events:       ' `cut -d',' -f5 < events.log | wc -l`
