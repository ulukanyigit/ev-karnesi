#!/bin/bash
# İl geneli: Geofabrik Türkiye -> İstanbul -> ilçe başına PBF -> Overpass biçimli JSON
set -e
cd /home/claude/evk
U="/mnt/user-data/uploads/EV KARNESİ/data/raw"
mkdir -p prov && cd prov
if [ ! -f turkey.osm.pbf ]; then cat "$U/turkey-latest.osm.pbf.part1" "$U/turkey-latest.osm.pbf.part2" > turkey.osm.pbf; fi
osmium extract -b 27.90,40.76,29.98,41.62 turkey.osm.pbf -o ist.osm.pbf --overwrite -s smart
osmium fileinfo ist.osm.pbf | grep -E "Size|Timestamp|header"
osmium tags-filter ist.osm.pbf r/admin_level=6 -o adm6.osm.pbf --overwrite
osmium export adm6.osm.pbf -o adm6.geojson --overwrite --geometry-types=polygon
osmium tags-filter ist.osm.pbf w/natural=coastline -o coast.osm.pbf --overwrite
osmium export coast.osm.pbf -o coast.geojson --overwrite --geometry-types=linestring
echo PREP DONE
