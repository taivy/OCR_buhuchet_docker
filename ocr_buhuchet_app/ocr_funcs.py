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



def ocr_buhuchet(data, debug_mode=False):
    if debug_mode:
        import numpy as np
        from PIL import ImageFont, ImageDraw, Image
        import cv2
        
    data = json.loads(data)
        
    code_x_1 = None
    code = None    
    
    for page in data['results'][0]['results'][0]['textDetection']['pages']:
        # ищем ячейку "код"
        for smth in page['blocks']:
            for line in smth['lines']:
                line_bb = line['boundingBox']['vertices']
                line_string = ''.join([word['text'] for word in line['words']])
                '''
                if debug_mode:
                    cv2.putText(img,line_string, (int(line_bb[0]['x']), int(line_bb[0]['y'])), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0,0,255))
                '''
                if 'код' in line_string.lower():
                    code_x_1 = int(line_bb[0]['x'])
                    #x_2 = int(line_bb[2]['x'])
                    code_y_1 = int(line_bb[0]['y'])
                    code_y_2 = int(line_bb[2]['y'])
                    
                    '''
                    if debug_mode:
                        draw.rectangle(((int(line_bb[0]['x']), code_y_1), (int(line_bb[2]['x']), code_y_2)), fill=(0,255,255))
                    '''
                    
                    # максимальное расстояние, на которое должны отличаться
                    # y координаты ячейки "Код" и ячеек с датами
                    dates_max_threshold = 5*(code_y_2 - code_y_1)
                    
                    
                    break
    
    date_cell = ''
    dates = []
    first_cell = True
    date_cell_threshold = 90
    # dates_x содержит x координаты (левая и правая границы) дат и сами даты
    dates_x = []
    # codes_y содержит у координаты (верхняя и нижняя границы) кодов и сами коды
    codes_y = []
    # codes_nums содержит числа (из ячеек) для каждого кода
    codes_nums = dict()
    
    for page in data['results'][0]['results'][0]['textDetection']['pages']:
        # ищем ячейки с кодами и датами, сохраняем их текст и координаты
        for smth in page['blocks']:
            for line in smth['lines']:
                line_bb = line['boundingBox']['vertices']
                line_string = ''.join([word['text'] for word in line['words']])
                if abs(code_x_1 - int(line_bb[0]['x'])) < 80:
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
                    if code_x_1 > int(line_bb[0]['x']):
                        # ячейка находится левее ячейки "Код", пропускаем
                        continue
                    if first_cell:
                        # максимальное расстояние, на которое должны отличаться
                        # x координаты строк для одной ячейки с датой
                        date_cell_threshold = 1.2*(int(line_bb[0]['x']) - code_x_1)
                        first_cell = False
                    for date_string_dict in dates_x:
                        # проверяем каждую найденную ячейку с датой
                        # чаще всего в ячейке с датой несколько строк, нужно
                        # их объединить
                        date_x = date_string_dict['x']
                        if abs(date_x - int(line_bb[0]['x'])) < date_cell_threshold:
                            # если x координаты строки для ячейки с датой и 
                            # распознанной строки не сильно отличаются, то 
                            # относим строку к данной ячейке с датой, 
                            # т.е. добавляем строку к существующей
                            date_string_dict['content'] += ' ' + line_string
                            continue
                    else:
                        # если ещё нет ячейки с такими x координатами, то 
                        # создаём новую
                        date_string_dict = dict()
                        date_string_dict['x'] = int(line_bb[0]['x'])
                        date_string_dict['content'] = line_string
                        dates_x.append(date_string_dict)
    
    dates_x.append(date_string_dict) # добавляем последний словарь
    
    dates_new_x = []
    months_re = '(январ|феврал|март|апрел|май|мая|июн|июл|август|сентябр|октябр|ноябр|декабр)'
    date_string_to_parse_tuple = namedtuple('date_string_to_parse', 'content datestr_type')
    datestr_type_date_pattern = re.compile('(\d{1,2})\s*' + months_re + '\w*\s*([\d]{4})')
    datestr_type_months_pattern = re.compile(months_re + '([А-Яа-я\-]*\s*)*' + months_re + '[А-Яа-я\-]*\s*([\d]{4})')
    #print('DATES ', dates_x)
    for date_str_dict in dates_x:
        try:
            # относим строки с датами к одному из типов: дата или месяцы, сохраняем типы
            if datestr_type_date_pattern.search(date_str_dict['content']) is not None:
                date_string_to_parse = date_string_to_parse_tuple(date_str_dict['content'], 'date')
                dates_new_x.append(date_string_to_parse)
            elif datestr_type_months_pattern.search(date_str_dict['content']) is not None:
                date_string_to_parse = date_string_to_parse_tuple(date_str_dict['content'], 'months')
                dates_new_x.append(date_string_to_parse)
        except Exception as e:
            print(e)
            continue
    
    dates.append(date_cell) # добавляем последнее
    dates_formatted = []
    
    for date_string_to_parse in dates_new_x:
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
            date = month1 + '-' + month2 + '.' + year
        if date not in dates_formatted:
            dates_formatted.append(date)
    #print('DATES PARSED', dates_formatted)
    
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
            threshold = 1.2*(code_y_2 - code_y_1)
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
                            num = re.search('\(*([0-9]+)\)*', num).group(0)
                        except:
                            continue
                        codes_nums[code['name']].append(num)
                        
                        
    # итоговый словарь с кодами и датами
    codes_dates_dict = dict()
    
    for code, values in codes_nums.items():
        codes_dates_dict[code] = dict()
        # в codes_nums для каждого кода значения должны идти в правильном
        # порядке (слева направо), чтобы присваивались правильные даты
        for ind, value in enumerate(values):
            try:
                codes_dates_dict[code][dates_formatted[ind]] = value
            except:
                #print('Index error: ', code, ind, value)
                pass
    return codes_dates_dict

