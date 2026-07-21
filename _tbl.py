import sqlite3
c=sqlite3.connect('database/avs.db')
print(sorted(r[0] for r in c.execute("select name from sqlite_master where type='table'")))
