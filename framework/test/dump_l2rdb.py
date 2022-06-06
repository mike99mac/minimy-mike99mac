import dbm
db = dbm.open('framework/services/l2rdb/local2remote.db','r')
print("%s entries" % (len(db),))
k = db.firstkey()
while k is not None:
    print("%s--->%s" % (k, db[k]))
    k = db.nextkey(k)

