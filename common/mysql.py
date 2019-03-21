# -  *  - coding:utf-8  -  *  -

import pymysql
# from config.globalconfig import host, password, port, user

from common.log import Log

log = Log()


class Mysql(object):

    def __init__(self):
        try:
            self.conn = pymysql.connect(host=host, port=port, user=user, password=password, database="test")
            self.cursor = self.conn.cursor()
        except:
            log.error("connect error")

    def query_one(self, query):
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        if not result:
            log.error("not found--->{}".format(query))
        return result

    def __del__(self):
        self._close_db()

    def query_all(self, sql):
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        if not result:
            log.error("not found--->{}".format(query))
        return result

    def _close_db(self):
        self.cursor.close()
        self.conn.close()


if __name__ == "__main__":
    mysql = Mysql()
    query = """select * from student where s_id = '0111'"""
    result = mysql.query_one(query)
    print(result)
    sql = """select * from student where s_id > '01'"""
    res = mysql.query_all(sql)
    print(res)
