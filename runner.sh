cd /home/rprs/src/church_community_prayers/
python3 main.py print > current.txt
mail -s "peticiones comunales" -r $1 $2 < current.txt
# python3 main.py update
# rm current.txt
