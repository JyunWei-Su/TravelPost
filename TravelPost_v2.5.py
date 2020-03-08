'''
    1.1版：註解、API_KEY
    1.3版：修正直式圖片顯示預覽時比例異常的情形
    1.4版：正反面修正(圖片為反面)、使用geopy取得地點
    1.5版：完全使用geopy使用地點(刪除舊版method)
    1.6版：修正連線檢查ping次數(預設4次修正為1次)
       　　修正臺灣行政地理層級錯誤(台灣省)
    1.7版：tkinter改版
    1.8版：明信片新增TAG、使用者描述；修正圖片面文字偏移
    1.9版：新增註解、程式區段整理
    2.0版：必要檔案路徑修正、修正製作明信片時GUI無回應之問題
    2.1版：使用絕對路徑(始可打包)、文字大小及色彩調整
    2.2版：tkintere改版(所有元件放入框架中
    2.3版：區段整理、程式註解
    2.4版：修正誤判郵遞區號為地名的bug
    2.5版：讀入相片時，會提供預覽
'''
import requests                             #網路資料抓取
import cv2, exifread, numpy as np           #圖片處理
import wikipedia                            #維基百科查詢
import string                               #字串處理
from PIL import ImageFont, ImageDraw, Image, ImageTk #圖片處理
from geopy.geocoders import Nominatim       #geopy(地理資訊獲取)
from langconv import *                      #簡字轉繁字
import tkinter as tk                        #用戶介面(下同)
import tkinter.filedialog ,tkinter.messagebox
import os, sys, datetime                    #系統、系統時間
import threading                            #多執行緒
from pathlib import Path                    #檔案系統路徑

inFile_path = ''                            #來源影像檔名
now = ''                                    #現在時間(用來記錄用戶按下按鈕的時間

def getWiki(term): #查詢維基百科介紹
    wikipedia.set_lang('zh')                        #設定為中文
    text = wikipedia.summary(term, sentences=1)     #抓取一句介紹
    text = Converter('zh-hant').convert(text)       #將簡字轉為繁字
    #將括號內容清除
    for char in ['(', ')', '[', ']', '（', '）']:
        text = text.replace(char, '|')
    article_list = text.split('|')
    n = 0
    text = ''
    for item in article_list:
        if((n % 2) == 0):
            text += item
        n +=1
    #若段落過長，移除最長的句子
    while(len(text)>81):
        sentence_list = text.split('，')
        len_sentence = []
        for i in range(len(sentence_list)):
            len_sentence.append(len(sentence_list[i]))
        len_max = max(len_sentence)
        for i in range(len(sentence_list)):
            if(len(sentence_list[i]) == len_max):
                sentence_list.remove(sentence_list[i])
                break
        text = '，'.join(sentence_list)  
    return text #回傳地點介紹

def findLocationName(Coordinate): #依GPS座標取得地名與介紹(使用geopy)
    global now
    #嘗試透過geopy獲取地名
    try:
        geolocator = Nominatim(user_agent='TravelPost' + now, timeout = 10)
        location = str(geolocator.reverse(Coordinate))
        '''format:地名, 村里, 鄉鎮, 縣市, 區省, 郵遞號, 國家'''
        print('...Loaction: ' + location)
    except:
        print('...geolocator_Err', end ='')
        return ('', '疊嶂峰上明月羞、翠光浮動萬山秋。')
    loc_lists = location.split(', ')            #將地址字串轉為list
    if(loc_lists[-1] == 'Taiwan'):              #修正臺灣行政地理層級錯誤(台灣省)
        loc_lists[-1] = '台灣'
        if '臺灣省' in loc_lists :
            loc_lists.remove('臺灣省')
        try:
            P_code = int(loc_lists[-2])
            loc_lists.remove(loc_lists[-2])
        except:
            pass
    loc_lists = [ loc_lists[-1].split(' ')[0], loc_lists[-2] ]
    Location = loc_lists[0] + ' ' + loc_lists[1]#format:['國家', '城市']
    for char in ['縣', '市', '県']:             #行政級別刪除
        Location = Location.replace(char, '')
    Introduction = getWiki(loc_lists[0])        #呼叫 getWiki 取得"國家"介紹
    print('...findLocationName_OK')
    return (Location, Introduction) #回傳地點與介紹

def coordinateConvert(coordinate): #GPS座標換算(60進位 to 10進位)
    '''input format: '[nn, mm, aa/bb]' (60進位,百分位為分數)'''
    coordinate = coordinate.replace(' ', '')    #移除空白
    coordinate = coordinate.replace('[', '')    #移除左中括號
    coord_2_a = (coordinate[coordinate.rfind(',') + 1:coordinate.rfind('/')])   #取得百分位數值分母
    coord_2_b = (coordinate[coordinate.rfind('/') + 1:coordinate.rfind(']')])   #取得百分位數值分子
    coordinate = coordinate.replace('/', '').replace(']', '')                   #移除左斜和右括號
    coordinate = coordinate.split(',')                  #此時fomat 'nn,nn,aa/bb'，分割為list
    coordinate[2] = int(coord_2_a) / int(coord_2_b)     #計算百分位之分數
    coordinate = int(coordinate[0]) + int(coordinate[1])/60 + coordinate[2]/600 #計算座標十進位值
    coordinate = round(coordinate, 6)                   #小數取6位
    return coordinate

def analyzePicture(inFile_path): #分析照片資訊，取得時間及GPS
    f = open(inFile_path, 'rb')
    tags = exifread.process_file(f)
    #嘗試讀取GPS資訊
    try:
        Latitude = str(tags['GPS GPSLatitude'])
        Latitude = coordinateConvert(Latitude)
        Longitude = str(tags['GPS GPSLongitude'])
        Longitude = coordinateConvert(Longitude)
        Coordinate = str(Latitude) + ', ' + str(Longitude) #geopy_format
    except:
        Coordinate = 'Null'
        print('GPS讀取失敗')
    #嘗試讀取時間(GPS資料優先)
    try:
        try:
            Time = str(tags['GPS GPSDate'])
            Time = Time.replace(':', '.')
        except:
            Time = str(tags['Image DateTime'])
            Time = Time.replace(':', '.')
            Time = Time.split(' ')[0]
    except:
        Time = 'Fascinating.'
        print('時間讀取失敗')
    print('...analyzePicture_OK')
    return (Time, Coordinate)

def mainPictureAddText(Location, Time): #繪製明信面反面(風景
    bk_img = cv2.imread(inFile_path)
    (x,y,z) = bk_img.shape          #取得相片的長與寬(x,y)，z在這裡用不到
    text_x = int(0.05*y)            #設定文字x座標
    text_y = int(0.9*x)             #設定文字y座標
    text = Location + ' ' + Time    #設定文字(國家名稱 + 時間(日期) )
    backClor =(102, 102, 102)       #設定字卡底色
    font = ImageFont.truetype(str(Path(sys.argv[0]).parent.joinpath('font_MicrosoftJhengHei.ttf')), y//30) #設定字體與字型大小
    (width, heigh), (offset_x, offset_y) = font.font.getsize(text) #取得文字方框大小
    #繪製字卡
    r = int(heigh / 2)
    bk_img = cv2.rectangle(bk_img, (text_x, text_y), (text_x + width, text_y + heigh), backClor, -1) #繪製方框
    bk_img = cv2.circle(bk_img, (text_x, text_y + r), r, backClor, -1)          #繪製左圓
    bk_img = cv2.circle(bk_img, (text_x + width, text_y + r), r, backClor, -1)  #繪製右圓
    #繪製文字
    img_pil = Image.fromarray(bk_img)
    ImageDraw.Draw(img_pil).text((text_x , text_y - offset_y), text , font = font, fill = (255, 255, 255) ) #繪製文字
    bk_img = np.array(img_pil)
    #寫入並回傳長寬
    cv2.imwrite(str(Path(sys.argv[0]).parent.joinpath('postcard_' + now + '_back.jpg')),bk_img)
    print('...mainPictureAddText_OK')
    return(max(x,y), min(x,y)) #回傳長與寬(這裡設定寬>=長

def makePostcard(x, y, introduction, textTag, textUsr):             #繪製明信片正面(郵務
    postcard = np.zeros((y, x, 3), dtype="uint8")                   #開新畫布
    cv2.rectangle(postcard, (0, 0), (x, y), (255, 255, 255), -1)    #填滿背景色(白色)
    cv2.rectangle(postcard, (int(x*0.6), int(y*0.05)), (int(x*0.6), int(y*0.95)), (68, 68, 68), y//100)             #繪製中間隔線
    for n in [0.7, 0.8, 0.9]:                                       #繪製地址欄格線3條
        cv2.rectangle(postcard, (int(x*0.65), int(y*n)), (int(x*0.95), int(y*n)), (68, 68, 68), 1+y//300)
    cv2.rectangle(postcard, (int(x*0.95), int(y*0.05)), (int(x*0.95 - y*0.2), int(y*0.35)), (68, 68, 68), 1+y//300) #繪製郵票框
    cv2.imwrite(str(Path(sys.argv[0]).parent.joinpath('postcard_' + now + '_front.jpg')), postcard) #先寫檔
    
    #繪製文字(國家介紹、個人敘述、Tag)
    img = cv2.imread(str(Path(sys.argv[0]).parent.joinpath('postcard_' + now + '_front.jpg'))) #讀檔
    img_pil = Image.fromarray(img)                      #繪版
    #繪製國家介紹文字
    font_itr = ImageFont.truetype(str(Path(sys.argv[0]).parent.joinpath('font_MicrosoftJhengHei.ttf')), y//30)      #設定需要顯示的字體與大小
    font_usr = ImageFont.truetype(str(Path(sys.argv[0]).parent.joinpath('font_HuakangBamboo.ttc')), y//25)
    #取得27個字文字框大小並檢查是否會超出版面(這裡設定27個字的版面最漂亮)
    (width, heigh), (offset_x, offset_y) = font_itr.font.getsize('這裡會有二七個字。這裡會有二七個字。這裡會有二七個字。')
    if (width > x*0.6): #檢查是否超出格式範圍(版面是否會異常)
        font_itr = ImageFont.truetype(str(Path(sys.argv[0]).parent.joinpath('font_MicrosoftJhengHei.ttf')), y//40)  #重新設定字體與大小
        font_usr = ImageFont.truetype(str(Path(sys.argv[0]).parent.joinpath('font_HuakangBamboo.ttc')), y//32)
    #繪製文字_國家介紹資訊(文字多時須分多行)
    introduction = '　　' + introduction    #開頭空兩格全形格
    if(len(introduction) <= 27):            #將段落分行
        introduction = [introduction]
        text_offset = 0.1
    elif(len(introduction) <=54):
        introduction = [introduction[0:26], introduction[27:]]
        text_offset = 0.05
    else:
        introduction = [introduction[0:26], introduction[27:53], introduction[54:]]
        text_offset = 0
    for sentence in introduction:           #繪製文字
        ImageDraw.Draw(img_pil).text((x*0.05 , y*(0.75 + text_offset)), sentence , font = font_itr, fill = (0, 0, 0) ) #繪製文字
        text_offset += 0.05
    #繪製文字_個人敘述
    text_offset = 0
    textUsr = '　　' + textUsr
    while(len(textUsr) > 0):    #每27字繪製一行
        ImageDraw.Draw(img_pil).text((x*0.05 , y*(0.1 + text_offset)), textUsr[0 : min(len(textUsr), 23)] , font = font_usr, fill = (255, 0, 0) ) #繪製文字
        textUsr = textUsr.replace(textUsr[0 : min(len(textUsr), 23)], '')
        text_offset += 0.05     #向下偏移一個單位(0.05)
    #繪製文字_Tag
    Tag_lists = textTag.split('\n')
    font_tag = ImageFont.truetype(str(Path(sys.argv[0]).parent.joinpath('font_MicrosoftJhengHei.ttf')), y//25)
    (width, heigh), (offset_x, offset_y) = font_tag.font.getsize('中文字體') #取得中文字體高度
    n=0.7
    while(len(Tag_lists) > 0):  #每兩個Tag繪製一行
        text = Tag_lists[0]     #讀入第一個Tag
        Tag_lists.remove(Tag_lists[0]) #讀入後清除
        if(len(Tag_lists) > 0): #讀入第二個Tag並清除(若存在)
            text += ' '
            text += Tag_lists[0]
            Tag_lists.remove(Tag_lists[0])
        ImageDraw.Draw(img_pil).text((int(x*0.65) , int(y*n) - heigh -offset_y -(3+y//300)), text, font = font_tag, fill = (119, 0, 0) ) #繪製文字
        n += 0.1
    #寫檔
    img = np.array(img_pil)
    cv2.imwrite(str(Path(sys.argv[0]).parent.joinpath('postcard_' + now + '_front.jpg')),img)
    print('...makePostcard_OK')
    
def photoProcess(path, textTag, textUsr): #照片分析並製作明信片
    print(path)
    global now, inFile_path
    inFile_path = path
    now = datetime.datetime.now().strftime('%f')            #取得現在時間(作為輸出檔名)
    (Time, Coordinate) = analyzePicture(inFile_path)        #分析相片資訊(GPS、時間)
    if (os.system('ping -n 1 -w 100 8.8.8.8 ') != 0):       #如果無法連線到網路 連通為0
        (Location, Introduction) = ('', '疊嶂峰上明月羞、翠光浮動萬山秋。')
    elif (Coordinate == 'Null'):                            #如果抓不到地理資訊與介紹
        (Location, Introduction) = ('', '一片自然風景是一個心靈的境界。 —— 阿米爾')
    else:
        (Location, Introduction) = findLocationName(Coordinate) #取得地點名稱與介紹
    (weith, heigh) = mainPictureAddText(str(Location), Time)    #繪製明信片反面(圖案)
    makePostcard(weith, heigh, Introduction, textTag, textUsr)  #繪製明信片正面(郵務)
    print('Done.')
    return 'postcard_' + now #回傳輸出檔名

def main(): #主函數(用戶介面)
    #產生視窗並設定標題、解析度、背景色
    window = tk.Tk()
    window.title('Post Card Maker')
    window.geometry('1200x680')
    window.configure(background='lemon chiffon')

    path = ''
    def selectFile(): #建立選擇檔案函數，供按鈕元件呼叫
        filename = tk.filedialog.askopenfilename() #呼叫文件選擇器
        nonlocal path
        #檢查檔案格式
        if ('.jp' not in filename) and ('.JP' not in filename) :
            path = ''
            left_label.config(text = '尚未選擇檔案', bg = 'RosyBrown1')
            tkinter.messagebox.showerror(title='錯誤', message='未選取檔案或格式不支援。')  # 提出錯誤對話窗
        else:
            path = filename
            left_label.config(text = '檔案來源：' + path, bg = 'aquamarine')
            #提供預覽
            img_1 = Image.open(path)  
            (x,y) = img_1.size
            if y > x :
                (x,y) = (y,x)
                img_1 = img_1.transpose(Image.ROTATE_270)
            img_1 = img_1.resize((600,y*600//x))
            photo_1 = ImageTk.PhotoImage(img_1)
            img_1_label.config(image = photo_1)
            img_1_label.image = photo_1
            img_2_label.config(image = '')
        right_label.config(text = '尚未產生明信片', bg = 'RosyBrown1')

    def threadFunc(func, *args): #將函數打包進線程
        trd_func = threading.Thread(target=func, args=args) #創建
        trd_func.setDaemon(True) #守護
        trd_func.start() #啟動

    def process(): #建立圖片處理函數，供按鈕元件呼叫
        nonlocal path
        mak_btn.config(text = '明信片產生中...', bg = 'salmon')
        textTag = (tag_text.get(1.0, 'end') + 'End').replace('\nEnd','')
        textUsr = (usr_text.get(1.0, 'end') + 'End').replace('\nEnd','')
        try:
            out_file = photoProcess(path, textTag, textUsr) #照片分析並製作明信片
            #取得輸出檔案並調整大小以適合瀏覽
            right_label.config(text = '輸出成功：' + out_file, bg = 'aquamarine')
            img_1 = Image.open(str(Path(sys.argv[0]).parent.joinpath(out_file + '_back.jpg')))
            img_2 = Image.open(str(Path(sys.argv[0]).parent.joinpath(out_file + '_front.jpg')))
            (x,y) = img_1.size
            if y > x :
                (x,y) = (y,x)
                img_1 = img_1.transpose(Image.ROTATE_270)
            img_1 = img_1.resize((600,y*600//x))
            img_2 = img_2.resize((600,y*600//x))
            #更新並顯示預覽圖片
            photo_1 = ImageTk.PhotoImage(img_1)
            img_1_label.config(image = photo_1)
            img_1_label.image = photo_1
            photo_2 = ImageTk.PhotoImage(img_2)
            img_2_label.config(image = photo_2)
            img_2_label.image = photo_2
            #重置使用者介面
            tag_text.delete(1.0, 'end')
            usr_text.delete(1.0, 'end')
            mak_btn.config(text = '產生明信片', bg = 'SystemButtonFace')
            tkinter.messagebox.showinfo(title='輸出完成', message='輸出完成：'+ out_file)       #提示資訊對話窗
        except:
            mak_btn.config(text = '產生明信片', bg = 'SystemButtonFace')
            if(path == ''):
                tkinter.messagebox.showerror(title='錯誤', message='請先選擇檔案')              #提出錯誤對話窗
            else:
                tkinter.messagebox.showerror(title='錯誤', message='發生意外錯誤，請重新操作')  #提出錯誤對話窗
            path = ''
            left_label.config(text = '尚未選擇檔案', bg = 'RosyBrown1')

    #標頭介紹文字
    header_label_frame = tk.Frame(window, width = 1200, height=60)
    header_label_frame.pack_propagate(0)
    header_label_frame.pack(side=tk.TOP)
    header_label = tk.Label(header_label_frame, text='你好！歡迎使用明信片產生器，請『選擇照片』並點選『產生明信片』。\n『TAG』及『個人敘述』可選擇性輸入', bg='light sky blue')
    header_label.pack(fill=tk.BOTH, expand=True)
    '''功能區元件配置(為了版面配置，所有元件置於框架中)'''
    #功能區框架
    func_frame = tk.Frame(window) 
    func_frame.pack(side=tk.TOP)
    #文字元件
    left_label_frame = tk.Frame(func_frame, width = 525, height=60)
    left_label_frame.pack_propagate(0)
    left_label_frame.pack(side=tk.LEFT)
    left_label = tk.Label(left_label_frame, text='尚未選擇檔案', bg = 'RosyBrown1', height=3) #左
    left_label.pack(fill=tk.BOTH, expand=True)
    
    right_label_frame = tk.Frame(func_frame, width = 525, height=60)
    right_label_frame.pack_propagate(0)
    right_label_frame.pack(side=tk.RIGHT)
    right_label = tk.Label(right_label_frame, text='尚未產生明信片', bg = 'RosyBrown1', height=3) #右
    right_label.pack(fill=tk.BOTH, expand=True)
    
    #按鈕元件
    btn_frame = tk.Frame(func_frame, width = 150, height=60)
    btn_frame.pack_propagate(0)
    btn_frame.pack(side=tk.TOP)
    slt_btn = tk.Button(btn_frame, text='選擇圖片', width = 20, command = selectFile)
    slt_btn.pack(fill=tk.BOTH, expand=True)
    mak_btn = tk.Button(btn_frame, text='產生明信片', width = 20, command = lambda:threadFunc(process))
    mak_btn.pack(fill=tk.BOTH, expand=True)
    
    #使用者輸入框架
    usr_frame = tk.Frame(window) 
    usr_frame.pack(side=tk.TOP)
    
    #文字元件及文字框元件
    tag_label_frame = tk.Frame(usr_frame, width = 150, height=60)
    tag_label_frame.pack_propagate(0)
    tag_label_frame.pack(side=tk.LEFT)
    tag_label = tk.Label(tag_label_frame, text='TAG(1行1個)', bg = 'pale green')
    tag_label.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    tag_text_frame = tk.Frame(usr_frame, width = 375, height=60)
    tag_text_frame.pack_propagate(0)
    tag_text_frame.pack(side=tk.LEFT)
    tag_text = tk.Text(tag_text_frame)
    tag_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    usr_label_frame = tk.Frame(usr_frame, width = 150, height=60)
    usr_label_frame.pack_propagate(0)
    usr_label_frame.pack(side=tk.LEFT)
    usr_label = tk.Label(usr_label_frame, text='個人敘述', bg = 'pale green')
    usr_label.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    usr_text_frame = tk.Frame(usr_frame, width = 525, height=60)
    usr_text_frame.pack_propagate(0)
    usr_text_frame.pack(side=tk.LEFT)
    usr_text = tk.Text(usr_text_frame)
    usr_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
    
    #圖片元件(未產生明信片時不會有東西)
    img_1_label = tk.Label(window)
    img_1_label.pack(side=tk.LEFT)
    img_2_label = tk.Label(window)
    img_2_label.pack(side=tk.RIGHT)

    window.mainloop() #呼叫視窗運作
    
try:
    main()
except:
    print('很抱歉，發生意外錯誤。')





