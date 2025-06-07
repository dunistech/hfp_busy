import mysql.connector

con = mysql.connector.connect(
    # host='securecryptosrecovery.com',
    host='195.250.27.35',
    user='securecr',
    database='securecr_salesnet_data',
    password='kz7Yp2tAO2)]8Z',
    port=3306,

)

if con.is_connected:
    print('yes')
else:
    print('no')