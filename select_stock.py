# -*- coding: utf-8 -*-
import yagmail
import contextlib
import requests,json
import tushare as ts
import copy,sys,pymysql,time
from datetime import datetime
from bs4 import BeautifulSoup
class select_stock():
    def __init__(self):
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
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflat',
            'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.100 Safari/537.36',
            'Host': 'www.iwencai.com',
            'Connection':'keep-alive',
            'Cache-Control':'max-age=0'
        }
        self.resession=requests.Session()
        self.index_dic={
            '_stk-code_' : 'code_index',
            '_stk-name_' : 'name_index',
            '最新价' : 'price_index',
            '涨跌幅:前复权' : 'change_index',
            'dde大单净量' : 'bigdan_index',
            'a股市值(不含限售股)' : 'marketvalue_index',
            '开盘价:前复权' : 'openprice_index',
            '最高价:前复权' : 'hightprice_index',
            '最低价:前复权' : 'lowprice_index',
            '收盘价:前复权' : 'closeprice_index',
            '振幅' : 'zf_index',
            '成交量' : 'volume_index',
            'dde大单净流入量' : 'bigdan_purein_index',
            '流通a股' : 'marketvalue_index',
            'dde散户数量' : 'dde_shsl_index',
            '买入信号inter' : 'buy_signalinter_index',
            '技术形态' : 'tech_simbol_index',
            '市净率(pb)' : 'pb_index',
            '市盈率(pe)' : 'pe_index',
            '市销率(ps)' : 'ps_index',
            '总市值' : 'total_marketvalue_index',
            '所属同花顺行业' : 'jqka_industry_index',
            '上市天数' : 'daystomarket_index'
        }
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
    def get_buy_code_old(self,url):
        code = self.resession.get(url,headers=self.headers).text
        soup = BeautifulSoup(code, "lxml")
        dic={}
        result=[]
        for one in soup(class_='em graph alignCenter graph'):
            name = one.find('a').text
            code = one.find('a').attrs['href'][-6:]
            dic['name']=name
            dic['code']=code
            result.append(copy.deepcopy(dic))
        return result
    def get_buy_code(self,url):
        code = requests.get(url,headers=self.headers).text
        start=code.find('var allResult')
        print('start',start)
        end=code.find('};',start)
        code=code[start+16:end+1]
        print('end:',end)
        print(code)
        if code:
            json_code=json.loads(code)
            for i,title in enumerate(json_code['indexID']):
                if title=='_stk-code_' : code_index=i
                if title=='_stk-name_' : name_index=i
                if title=='a股市值(不含限售股)' : marketvalue_index=i
            results=json_code['result']
            dic={}
            result_=[]
            for result in results:
                dic['name']=result[name_index]
                dic['code']=result[code_index][0:6]
                dic['market_value']=result[marketvalue_index]
                result_.append(copy.deepcopy(dic))
            print(result_)
            return result_

    def save_stock(self,stocks=None,stype=1):
        print(stocks)
        if not stocks:
            return
        with self.mysql_connnect() as cursor:
            sql= 'insert into zy_stock (code,name,date,type) values'
            if type(stocks)=='dict':
                p=[]
                p.append(stocks)
                stocks=p
            if len(stocks)>1:
                stocks=stocks[:1]
            l=[]
            for stock in stocks:
                today = str(datetime.today())
                sql_="('"+stock['code']+"','"+stock['name']+"','"+today+"',"+str(stype)+")"
                l.append(sql_)
            sql=sql+",".join(l)
            print(sql)
            cursor.execute(sql)
    def sendmail(self,title,body):
        yag = yagmail.SMTP(user='20728850@qq.com', password='zxj99879', host='smtp.qq.com', port='25')
        yag.send(to='20728850@qq.com', subject=title, contents=[body])
        print("已发送邮件")
    def strategy4(self):
        url="http://www.iwencai.com/stockpick/search?typed=1&preParams=&ts=1&f=1&qs=result_rewrite&selfsectsn=&querytype=&searchfilter=&tid=stockpick&w="
        word4="非创业板；涨跌幅小于9.5；上市天数小于100；流通市值从小到大排列前2"
        four=self.get_buy_code(url+word4)
        if four:
            str4="<h3>策略4：</h3>"
            for dic in four:
                str4=str4+dic['name']+dic['code']+"<br>"
            self.sendmail("策略4:"+str(len(four))+"支",str4)
        else:
            self.sendmail("今日策略4无选股","今日没有股票可选")
        return four
    def is_over_ma5(self):
        cyb_data=ts.get_hist_data('399678')
        close=cyb_data[0:1]['close'][0]
        ma5=cyb_data[0:1]['ma5'][0]
        if close>ma5:
            return True
        else:
            return False
    def get_stock_info(self,stock_code):
        time.sleep(5)
        url="http://www.iwencai.com/stockpick/search?w="+str(stock_code)+'+流通市值'
        soup = BeautifulSoup(self.resession.get(url,headers=self.headers).text,'lxml')
        market_value=soup(class_='upright_table')[0].find_all('tr')[0].find('a').text
        total_value=soup(class_='upright_table')[0].find_all('tr')[1].find('a').text
        stock_info={}
        stock_info['market_value']=market_value
        stock_info['total_value']=total_value
        return stock_info
    def get_floatshares(self,code):
        url='https://api.wmcloud.com/data/v1//api/equity/getEqu.json?field=&listStatusCD=&secID=&ticker='+code+'&equTypeCD=A'
        if not ts.get_token():
            ts.set_token('88a5361b35519f365204192456b7025a537cfaca5713a4ce19e6ae47cc9256c5')
        headers = {"Authorization": "Bearer " +  ts.get_token(),"Accept-Encoding": "gzip, deflate"}
        info=requests.get(url,headers=headers).text
        info=json.loads(info)
        return info['data'][0]['nonrestFloatShares']
    def get_price(self,code):
        day=datetime.now().strftime('%Y-%m-%d')
        price=ts.get_k_data(code,start=day)
        basics=ts.get_stock_basics()
        return price
    def get_market_value(self,code):
        stock_info={}
        market_value=float(self.get_floatshares(code))*float(self.get_price(code)['close'])
        stock_info['market_value']=market_value
        return stock_info
    def lowest_value(self):
        root="http://www.iwencai.com/stockpick/search?w="
        keyword1='涨跌幅大于4.5；dde大单净量大于1；长上影线；市净率小于12；流通市值从小到大排列'
        #keyword1=None
        keyword2='涨跌幅大于4.7；dde大单净量大于0.7；上影线大于3.7；市净率小于12；流通市值从小到大排列'
        keyword3='散户数量小于-100；涨跌幅大于4.7；dde大单净量大于0.5；上影线大于3.5；市净率小于12；流通市值从小到大排列'
        if not self.is_over_ma5():
            preword='上市天数大于160;'
            keyword1=preword+keyword1 if keyword1 else None
            keyword2=preword+keyword2
            keyword3=preword+keyword3
        stock={}
        str_all=''
        if keyword1:
            stock1=self.get_buy_code(root+keyword1)
            time.sleep(5)
            if stock1:
                str1="<h3><a href='"+root+keyword1+"'>策略1：</a></h3>"
                for dic in stock1:
                    str1=str1+dic['name']+dic['code']+"<br>"
                str_all+=str1
#                try:
#                    stock_info=self.get_market_value(stock1[0]['code'])
#                except:
#                    stock_info=self.get_stock_info(stock1[0]['code'])
#                stock1[0]['market_value']=stock_info['market_value']
                stock=stock1[0]
        stock2=self.get_buy_code(root+keyword2)
        time.sleep(5)
        if stock2:
            str2="<h3><a href='"+root+keyword2+"'>策略2：</a></h3>"
            for dic in stock2:
                str2=str2+dic['name']+dic['code']+"<br>"
            str_all+=str2
#            try:
#                stock_info=self.get_market_value(stock2[0]['code'])
#            except:
#                stock_info=self.get_stock_info(stock2[0]['code'])
#            stock2[0]['market_value']=stock_info['market_value']
            if not stock:
                stock=stock2[0]
            elif stock['market_value']>stock2[0]['market_value']:
                stock=stock2[0]
        stock3=self.get_buy_code(root+keyword3)
        if stock3:
            str3="<h3><a href='"+root+keyword3+"'>策略3：</a></h3>"
            for dic in stock3:
                str3=str3+dic['name']+dic['code']+"<br>"
            str_all+=str3
#            try:
#                stock_info=self.get_market_value(stock3[0]['code'])
#            except:
#                stock_info=self.get_stock_info(stock3[0]['code'])
#            stock3[0]['market_value']=stock_info['market_value']
            if not stock:
                stock=stock3[0]
            elif stock['market_value']>stock3[0]['market_value']:
                stock=stock3[0]
        if stock:
            url="http://wnqyf.com/weiphp/index.php?s=/addon/ShareUmbrella/Wap/stockadmin"
            self.sendmail("策略1:"+str(len(stock1))+"支;策略2:"+str(len(stock2))+"支;策略3:"+str(len(stock3))+"支","<a href='"+url+"'>查看计划</a><br>最低市值为："+str(stock['name'])+"<br>"+str_all)
        else:
            self.sendmail("今日策略1、2、3均无选股","今日没有股票可选")
        return stock
if __name__=='__main__':
    if sys.argv[1]=='strategy4':
        stock_=select_stock()
        stock=stock_.strategy4()
        stock_.save_stock(stock,0)
    if sys.argv[1]=='lowest':
        stock_=select_stock()
        stock=stock_.lowest_value()
        l=[]
        l.append(stock)
        stock_.save_stock(l)
    if sys.argv[1]=='test':
        root="http://www.iwencai.com/stockpick/search?w="
        keyword1='涨跌幅大于4.5；dde大单净量大于1；长上影线；市净率小于12；流通市值从小到大排列'
        stock_=select_stock()
        url=root+keyword1
        stock_.get_buy_code(url)

