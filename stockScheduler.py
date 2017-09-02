from apscheduler.schedulers.blocking import BlockingScheduler as Scheduler
from datetime import datetime
import contextlib,pymysql
import shipane_sdk
schedudler = Scheduler()
 
class stockScheduler():
    def __init__(self,client):
        self.db_config={
             'host':'wnqyf.com',
             'port':3306,
             'user':'wnq',
             'password':'wnq6',
             'db':'wnqyf',
             'charset':'utf8',
             'cursorclass':pymysql.cursors.DictCursor,
             }
        self.shipane=shipane_sdk.Client(host='106.14.216.218', port=8888, key='18106721982')
        self.client=client
        self.zxzq='account:3782'
        self.cfzq='account:2033'
    @contextlib.contextmanager
    def mysql_connnect(self):
        config = self.db_config
        db_connection = pymysql.connect(**config)
        cursor = db_connection.cursor()
        try:
            yield cursor
        finally:
            db_connection.commit()
            cursor.close()
            db_connection.close()
    def get_stock_price(self,stock_code=None):
        if stock_code==None:
            return None
        stock_code=str(stock_code)
        if (int(stock_code[0]) == 6):
            url = 'http://hq.sinajs.cn/list=sh' + stock_code
        else:
            url = 'http://hq.sinajs.cn/list=sz' + stock_code
        stock_info = requests.get(url).text.strip()
        stock_info = stock_info.split('=')[1]
        if stock_info=='':
            return None
        stock_info = stock_info.split(',')
        return_dic = {}
        return_dic['open_price'] = float(stock_info[1])
        return_dic['lastday_close'] = float(stock_info[2])
        return_dic['current_price'] = float(stock_info[3])
        return_dic['highest_price'] = float(stock_info[4])
        return_dic['lowest_price'] = float(stock_info[5])
        return_dic['buy1_price'] = float(stock_info[6]) if float(stock_info[6])>0 else float(stock_info[11])
        return_dic['sell1_price'] = float(stock_info[7])
        return_dic['buy1_volume'] = float(stock_info[10])
        return return_dic
    def get_could_buy(self):
        positions = self.connection.get_positions(self.client)
        sub_account = positions['sub_accounts']
        could_buy_money = float(sub_account.iat[0, self.type])
        return could_buy_money
    def get_could_sell(self,code):
        positions = self.connection.get_positions(client=self.client)
        holders = positions['positions']
        for index,row in holders.iterrows():
            if self.client==self.zxzq:
                stock_code = row[0]
                could_sell_amount = float(row[3])
            if self.client==self.cfzq:
                stock_code = row[1]
                could_sell_amount = float(row[4])
            if stock_code == code:
                 return could_sell_amount

    def get_scheduler(self):
        with self.mysql_connnect() as cursor:
            sql="select * from zy_stock_scheduler"
            cursor.execute(sql)
            result=cursor.fetchall()
        return result
    def action(self,stock):
        if not stock or not stock.get('code'):return
        code=stock.get('code')
        name=stock.get('name')
        action=stock.get('action')
        date=stock.get('date')
        time=stock.get('time')
        amount=stock.get('amount')
        money=stock.get('money')
        price=stock.get('price')
        if action=='buy':
            if not amount and not money:money=self.get_could_buy()
            if not price:price= self.get_stock_price(code)['sell1_price']
            if not amount:amount=int(money/price/100)*100
            self.shipane.buy(symbol=code, price=price,type='LIMIT', priceType=0,amount=amount,client=self.client)
        if action=='sell':
            if not price:price= self.get_stock_price(code)['buy1_price']
            if not amount:amount=self.get_could_sell(code)
            self.shipane.buy(symbol=code, price=price,type='LIMIT', priceType=0,amount=amount,client=self.client)


if __name__=="__main__":
    zxzq='account:3782'
    cfzq='account:2033'
#    schedudler.add_job(job1,'date',run_date=datetime(2017,9,2,14,47,0))
#    schedudler.add_job(job2,'cron',second="*/2")
#    schedudler.start()

    stockSched=stockScheduler(zxzq)
    r=stockSched.get_scheduler()

