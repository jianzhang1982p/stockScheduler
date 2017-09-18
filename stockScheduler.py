from apscheduler.schedulers.blocking import BlockingScheduler as Scheduler
from datetime import datetime
import contextlib,pymysql
import shipane_sdk,os,yagmail
import requests
import tushare as ts
class stockScheduler(object):
    def __init__(self,client):
        path=os.path.expanduser('~')
        f=open(path+"/.db_config","r")
        config = f.read()
        f.close()
        config=eval(config)
        self.db_config={
             'host':config['db_host'],
             'port':config['db_port'],
             'user':config['db_user'],
             'password':config['db_password'],
             'db':config['db_name'],
             'charset':'utf8',
             'cursorclass':pymysql.cursors.DictCursor,
             }
        self.mail_config={
            'host':config['mail_host'],
            'user':config['mail_user'],
            'password':config['mail_password'],
        }
        self.shipane=shipane_sdk.Client(host=config['shipane_host'], port=config['shipane_port'], key=config['shipane_key'])
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
        positions = self.shipane.get_positions(self.client)
        sub_account = positions['sub_accounts']
        if self.client==self.zxzq:
            could_buy_money = float(sub_account.iat[0, 3])
        if self.client==self.cfzq:
            could_buy_money = float(sub_account.iat[0, 2])
        return could_buy_money
    def get_could_sell(self,code):
        positions = self.shipane.get_positions(client=self.client)
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
    def delete_scheduler(self):
        with self.mysql_connnect() as cursor:
            sql="delete from zy_stock_scheduler where 1"
            cursor.execute(sql)
    def action(self,stock):
        print(stock)
        if not stock or not stock.get('code'):return
        code=stock.get('code')
        name=stock.get('name')
        action=stock.get('action')
        date=stock.get('date')
        time=stock.get('time')
        amount=stock.get('amount')
        money=stock.get('money')
        price=stock.get('price')
#        order = {
#            'action': 'BUY' if action == 'buy' else 'SELL',
#            'symbol': code,
#            'type': 'LIMIT',
#            'price': price,
#            'amount': amount
#        }
#        try:
#            self.shipane.execute(self.client, **order)
#        except Exception as e:
#            self._logger.exception("下单异常")
        try:
            if action=='buy':
                if not amount and not money:money=self.get_could_buy()
                if not price:price= self.get_stock_price(code)['sell1_price']
                if not amount:amount=int(money/price/100)*100
                self.shipane.buy(symbol=code, price=price,type='LIMIT', priceType=0,amount=amount,client=self.client)
            if action=='sell':
                if not price:price= self.get_stock_price(code)['buy1_price']
                if not amount:amount=self.get_could_sell(code)
                self.shipane.sell(symbol=code, price=price,type='LIMIT', priceType=0,amount=amount,client=self.client)
        except Exception as e:
            self.sendmail("操作流买卖错误！","操作流买卖错误请注意查看"+str(e))
    def sendmail(self,title,body):
        yag = yagmail.SMTP(user=self.mail_config['user'],
            password=self.mail_config['password'], host=self.mail_config['host'], port='25')
        yag.send(to='20728850@qq.com', subject=title, contents=[body])
        print("邮件已发送成功！"+title+body)
    def repo(self):
        repo_symbol='131810'
        df = ts.get_realtime_quotes(repo_symbol)
        print(df,df['bid'][0])
        order = { 
            'action': 'SELL',
            'symbol': repo_symbol,
            'type': 'LIMIT',
            'price': float(df['bid'][0]),
            'amountProportion': 'ALL'
        }
        try:
            client = self.client
            self.shipane.execute(client, **order)
        except Exception as e:
            print('客户端[%s]逆回购失败', client)
    def purchase_new_stocks(self):
        new_stocks=self.shipane.purchase_new_stocks(client=self.client)
def exitsched():
    schedudler.shutdown()
    exit()
if __name__=="__main__":
    zxzq='account:3782'
    cfzq='account:2033'
    #schedudler.add_job(job1,'cron',second="*/2",kwargs={'p':'ok'})
    #scheduler.add_job(tick, 'date', run_date='2016-02-14 15:01:05',args=['ok'])
    schedudler = Scheduler()
    stockSched=stockScheduler(cfzq)
    scheds=stockSched.get_scheduler()
    
    schedudler.add_job(exitsched,'cron',hour='15',minute='02')
    schedudler.add_job(stockSched.delete_scheduler,'cron',hour='15',minute='10')
    schedudler.add_job(stockSched.repo,'cron',hour='14',minute='58')
    schedudler.add_job(stockSched.purchase_new_stocks,'cron',hour='9',minute='50')
    
    if scheds:
        try:
            for sched in scheds:
                code=sched['code']
                print(code)
                rundate=sched['date']+' '+sched['time']
                #rundate='2017-09-03 23:23:00'
                rundate=datetime.strptime(rundate,'%Y-%m-%d %H:%M:%S')
                nowdate=datetime.now()
                if nowdate<rundate:
                    print(rundate)
                    schedudler.add_job(stockSched.action,'date',run_date=rundate,kwargs={'stock':sched})
        except Exception as e:
            print(e)
            schedudler.shutdown()
    schedudler.start()


