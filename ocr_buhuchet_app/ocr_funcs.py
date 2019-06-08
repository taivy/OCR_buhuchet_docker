import json
from itertools import chain
from collections import namedtuple
import re


months_dict = {
    "январ": '01',
    "феврал": "02",
    "март": "03",
    "апрел": "04",
    "май": "05",
    "мая": "05",
    "июн": "06",
    "июл": "07",
    "август": "08",
    "сентябр": "09",
    "октябр": "10",
    "ноябр": "11",
    "декабр": "12"   
}



def ocr_buhuchet(data, debug_mode=False, img_path=None):
    
    '''
    if debug_mode:
        import numpy as np
        from PIL import ImageFont, ImageDraw, Image
        import cv2
    '''
    
    data = json.loads(data)
    
    '''
    if img_path is not None:
        with open(img_path, 'rb') as f:
            bts = bytearray(f.read())
            numpyarray = np.asarray(bts, dtype=np.uint8)
            img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
    
    if debug_mode and (img is None):
        raise RuntimeError('No image for debug is provided')
    '''
    
    code_x_1 = None
    code = None    
    
    try:
        resp_results = data['results'][0]['results'][0]['textDetection']['pages']
        resp_results[0]['blocks']
    except KeyError:
        # на странице не распознан текст
        print('KeyError - pages or blocks')
        return {}
    
    
    for page in resp_results:
        # ищем ячейку "код"
        for block in page['blocks']:
            for line in block['lines']:
                line_bb = line['boundingBox']['vertices']
                line_string = ''.join([word['text'] for word in line['words']])
                
                '''
                if debug_mode:
                    cv2.rectangle(img, (int(line_bb[0]['x']), int(line_bb[0]['y'])), (int(line_bb[2]['x']), int(line_bb[2]['y'])), (0,0,255), 2)
                    font = ImageFont.truetype("DejaVuSans.ttf", 30, encoding='UTF-8')
                    img_pil = Image.fromarray(img)
                    draw = ImageDraw.Draw(img_pil)
                    #draw.text((int(line_bb[0]['x']), int(line_bb[0]['y'])), line_string, fill=(255,0,0), font=font)
                    img = np.asarray(img_pil)
                '''
                # строгое равенство а не in, т.к. может быть ситуация, когда
                # на странице есть код налового органа и другие коды
                
                if re.search(r'код(\s*(ни))*', line_string.strip().lower()) is not None:
                    code_x_1 = int(line_bb[0]['x'])
                    code_x_2 = int(line_bb[2]['x'])
                    code_y_1 = int(line_bb[0]['y'])
                    code_y_2 = int(line_bb[2]['y'])
                    
                    # максимальное расстояние, на которое должны отличаться
                    # y координаты ячейки "Код" и ячеек с датами
                    dates_max_threshold = 5*(code_y_2 - code_y_1)
                    break
    '''
    if debug_mode:
        img_pil.show()
    '''
    # на странице нет таблицы с кодами и датами, возвращаем пустой словарь 
    if not code_x_1:
        return {}
        
    date_cell = ''
    dates = []
    first_cell = True
    # dates_x содержит x координаты (левая и правая границы) дат и сами даты
    dates_x = []
    # codes_y содержит у координаты (верхняя и нижняя границы) кодов и сами коды
    codes_y = []
    # codes_nums содержит числа (из ячеек) для каждого кода
    codes_nums = dict()
    
    for page in data['results'][0]['results'][0]['textDetection']['pages']:
        # ищем ячейки с кодами и датами, сохраняем их текст и координаты
        for block in page['blocks']:
            for line in block['lines']:
                line_bb = line['boundingBox']['vertices']
                line_string = ''.join([word['text'] for word in line['words']])
                if abs(code_x_1 - int(line_bb[0]['x'])) < (code_x_2-code_x_1)*1.8:
                    try:
                        if re.search('[А-Яа-я]', line_string) is not None:
                            # если в ячейке буквы, то это не код
                            continue
                        int(line_string)
                        code = line_string
                    except:
                        # в коде могут быть случайно пробелы или скобки
                        try:
                            code = line_string.split(' ')[0]
                            code = code.split('(')[0]
                            code = code.split('|')[0]
                            int(code)
                        except:
                            # пропускаем код, если не получилось преобразовать в число
                            continue
                    code_y = dict()
                    code_y['name'] = code
                    y_1 = int(line_bb[0]['y'])
                    y_2 = int(line_bb[2]['y'])
                    code_y['y_1'] = y_1
                    code_y['y_2'] = y_2
                    codes_nums[code] = []
                    codes_y.append(code_y)
                elif abs(code_y_1 - int(line_bb[0]['y'])) < dates_max_threshold and abs(code_y_2 - int(line_bb[2]['y'])) < dates_max_threshold:
                    if code_x_1 > int(line_bb[0]['x']) or 'Форма' in line_string:
                        # ячейка находится левее ячейки "Код" или это надпись "форма", пропускаем
                        continue
                    if first_cell:
                        # максимальное расстояние, на которое должны отличаться
                        # x координаты строк для одной ячейки с датой
                        date_cell_threshold = 0.8*(int(line_bb[0]['x']) - code_x_1)
                        date_cell_width = int(line_bb[2]['x']) - int(line_bb[0]['x'])
                        first_cell = False
                    already_created = False
                    for date_string_dict in dates_x:
                        # проверяем каждую найденную ячейку с датой
                        # чаще всего в ячейке с датой несколько строк, нужно
                        # их объединить;
                        # собираем все строки, которые похожи на дату и их x
                        # координаты в dates_x, и для каждой ячейки, похожей
                        # на ячейку с датой (y координаты несильно отличаются
                        # от координат столбца с кодом) ищем строки, которые 
                        # относятся к ней
                        date_x = date_string_dict.get('x', None)
                        if not date_x:
                            # пропущенная дата с неизвестными координатами
                            continue
                        if abs(date_x - int(line_bb[2]['x'])) < date_cell_threshold:
                            # если x координаты строки для ячейки с датой и 
                            # распознанной строки не сильно отличаются, то 
                            # относим строку к данной ячейке с датой, 
                            # т.е. добавляем строку к существующей
                            date_string_dict['content'] += ' ' + line_string
                            already_created = True
                            break
                    if already_created:
                        continue
                    # если ещё нет ячейки с такими x координатами, то 
                    # создаём новую
                    date_string_dict = dict()
                    date_string_dict['x'] = int(line_bb[2]['x'])
                    date_string_dict['content'] = line_string
                    if dates_x:
                        if (abs(date_string_dict['x'] - dates_x[-1]['x'])) > date_cell_width*1.8:
                            # между новой и предыдущей датой должна была быть 
                            # ещё одна дата, но она не распозналась. вместо неё 
                            # ставим пустое значение, чтобы коды потом корректно 
                            # добавлялись
                            dates_x.append(dict(content='unknown'))
                    dates_x.append(date_string_dict)
    
    if debug_mode:
        print('CODES_Y:')
        print(codes_y)
        print()
        
        print('CODES_NUMS')
        print(codes_nums)
        print()
        
        print('DATES_X')
        print(dates_x)
        print()
    
    # на странице нет таблицы с кодами и датами, возвращаем пустой словарь 
    if not codes_y or not dates_x:
        return {}
    
    dates_x.append(date_string_dict) # добавляем последний словарь
    
    dates_new_x = []
    months_re = '(январ|феврал|март|апрел|май|мая|июн|июл|август|сентябр|октябр|ноябр|декабр)'
    date_string_to_parse_tuple = namedtuple('date_string_to_parse', 'content datestr_type')
    datestr_type_date_pattern = re.compile('(\d{1,2})\s*' + months_re + '\w*\s*([\d]{4})')
    datestr_type_months_pattern = re.compile(months_re + '([А-Яа-я\-]*\s*)*' + months_re + '[А-Яа-я\-]*\s*([\d]{4})')
    datestr_type_year_pattern = re.compile('\D*([\d]{4})\D*')
    
    if debug_mode:
        print('DATES:')
        for date in dates_x:
            print(date)
        print()
    
    for date_str_dict in dates_x:
        try:
            # относим строки с датами к одному из типов: дата или месяцы, сохраняем типы
            if datestr_type_months_pattern.search(date_str_dict['content'].lower()) is not None:
                date_string_to_parse = date_string_to_parse_tuple(date_str_dict['content'].lower(), 'months')
                dates_new_x.append(dict(content=date_string_to_parse, x=date_str_dict['x']))
            elif datestr_type_date_pattern.search(date_str_dict['content'].lower()) is not None:
                date_string_to_parse = date_string_to_parse_tuple(date_str_dict['content'].lower(), 'date')
                dates_new_x.append(dict(content=date_string_to_parse, x=date_str_dict['x']))
            elif datestr_type_year_pattern.search(date_str_dict['content'].lower()) is not None:
                date_string_to_parse = date_string_to_parse_tuple(date_str_dict['content'].lower(), 'year')
                dates_new_x.append(dict(content=date_string_to_parse, x=date_str_dict['x']))
                
        except Exception as e:
            continue
    
    dates.append(date_cell) # добавляем последнее
    dates_formatted = []

    for date_string in dates_new_x:
        
        date_string_to_parse = date_string['content']
        # парсим и форматируем данные в зависимости от типа
        if date_string_to_parse.datestr_type == 'date':
            date_string_parsed = datestr_type_date_pattern.search(date_string_to_parse.content)
            day = date_string_parsed.group(1)
            month = months_dict[date_string_parsed.group(2)]
            year = date_string_parsed.group(3)
            date = day + '.' + month + '.' + year
            
        if date_string_to_parse.datestr_type == 'months':
            date_string_parsed = datestr_type_months_pattern.search(date_string_to_parse.content)
            month1 = months_dict[date_string_parsed.group(1)]
            month2 = months_dict[date_string_parsed.group(3)]
            year = date_string_parsed.group(4)
            #date = month1 + '-' + month2 + '.' + year
            if month2 == '03':
                # март (1-й квартал)
                day = 31
            elif month2 == '06':
                # июнь (2-й квартал)
                day = 30
            elif month2 == '09':
                # сентябрь (3-й квартал)
                day = 30
            elif month2 == '12':
                # декабрь (4-й квартал)
                day = 31
            else:
                # квартал не распознан
                continue
            date = str(day) + '.' + month2 + '.' + year
        
        elif date_string_to_parse.datestr_type == 'year':
            date_string_parsed = datestr_type_year_pattern.search(date_string_to_parse.content)
            year = date_string_parsed.group(1)
            date = '31.12.' + year
            
        if date not in dates_formatted:
            dates_formatted.append(dict(date=date, x=date_string['x']))
    
    if debug_mode:
        print('DATES PARSED:')
        for date in dates_formatted:
            print(date)
        print()
    
    # sort lines and find nums
    for page in data['results'][0]['results'][0]['textDetection']['pages']:
        blocks = list(chain(page['blocks']))
        lines = []
        for block in blocks:
            for line in block['lines']:
                lines.append(line)
        offset = 0.1
        # сортируем строки по y координатам
        # offset и round в сортировке нужны, чтобы допускалась погрешность в координатах
        lines.sort(key = lambda line: (round(int(line['words'][0]['boundingBox']['vertices'][0]['y'])//2*offset), int(line['words'][0]['boundingBox']['vertices'][0]['x'])))
        for line in lines:
            line_bb = line['boundingBox']['vertices']
            line_string = ''.join([word['text'] for word in line['words']])
            # максимальное расстояние между у координатами для ячейкой с 
            # кодом и ячейки с данными
            threshold = code_y_2 - code_y_1
            for code in codes_y:
                # проверяем каждый код, и если его y координаты несильно 
                # отличаются от координат строки, то относим строку к коду
                y_1 = code['y_1']
                y_2 = code['y_2']
                if abs(y_1 - int(line_bb[0]['y'])) < threshold and abs(y_2 - int(line_bb[2]['y'])) < threshold:
                    '''
                    try:
                        num = int(line_string)
                    except ValueError:
                        continue
                    '''
                    num = line_string
                    if str(num) != code['name']:
                        # пропускаем, если нашли ячейку с кодом
                        try:
                            num = re.search('\(*([0-9]+\s*)+\)*', num).group(1)
                        except:
                            continue
                        codes_nums[code['name']].append(dict(val=num, x=int(line_bb[2]['x'])))
                        
                        
    # итоговый словарь с кодами и датами
    codes_dates_dict = dict()
    
    for code, values in codes_nums.items():
        codes_dates_dict[code] = dict()
        # в codes_nums для каждого кода значения должны идти в правильном
        # порядке (слева направо), чтобы присваивались правильные даты
        
        for d in values:
            #print('d x ', d['x'], d['val'])
            min_range = 100
            code_date = ''
            for date in dates_formatted:
                if abs(d['x'] - date['x']) < min_range:
                    min_range = abs(d['x'] - date['x'])
                    code_date = date['date']
            codes_dates_dict[code][code_date] = d['val']
    
    if debug_mode:
        print('RESULTS:')
        for result in codes_dates_dict:
            print(result)
            print(codes_dates_dict[result])
        print()
        
    return codes_dates_dict

