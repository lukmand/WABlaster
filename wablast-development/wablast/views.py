import json
import logging
import random
import string
import time
import pandas as pd
import socket
import subprocess
import os
import sys
import traceback
import datetime

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files import File

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from chromedriver_autoinstaller import install as chromedriver_install
from dotenv import load_dotenv

from threading import Thread, Event
from .util import *


load_dotenv()
BASE_URL = "https://web.whatsapp.com/"
CHAT_URL = "https://web.whatsapp.com/send?phone={phone}&text&type=phone_number&app_absent=1"
headers = {'content_type': 'application/json'}
HOST_NAME = socket.gethostname()
IP_ADDRESS = socket.gethostbyname(HOST_NAME)

# keep session_id and object reference of all open browsers
# implement LRU later
active_sessions = {

}

logger = logging.getLogger(__name__)
current_date = tools.get_datetime('%Y-%m-%d')

def create_instance(request):
    # Install ChromeDriver jika belum terinstal
    chromedriver_install()

    chrome_options = Options()
    chrome_options.add_argument("start-maximized")
    # user_data_dir = ''.join(random.choices(string.ascii_letters, k=8))
    user_data_dir = 'cache123'
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-data/" + user_data_dir)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-dev-shm-usage")
    #chrome_options.add_argument("--incognito")
    #chrome_options.add_experimental_option("detach", True)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # browser = webdriver.Chrome(
        # service=Service(ChromeDriverManager().install()),
        # options=chrome_options,
    # )
    browser = webdriver.Chrome(options=chrome_options)

    handles = browser.window_handles
    for _, handle in enumerate(handles):
        if handle != browser.current_window_handle:
            browser.switch_to.window(handle)
            browser.close()

    browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    # print(browser.execute_script("return navigator.userAgent;"))
    browser.get('https://www.httpbin.org/headers')

    # open new tab
    Browser.new_tab(browser)
    browser.get(BASE_URL)
    browser.maximize_window()

    # this make sure we have a list of all active session.
    # also keeping a global reference of this session/browser stops it from closing.
    # otherwise browser will close automatically after this function exists
    session_id = browser.__dict__.get('session_id')
    print(session_id)
    active_sessions[session_id] = browser

    f = open('session_id.txt', 'w')
    testfile = File(f)
    testfile.write(session_id)
    testfile.close
    f.close

    # reset session id soceng
    dialoge_session = open('log/dialogue_session_id.txt', 'w')
    dialoge_session.write('0')
    dialoge_session.close

    soceng_session = open('log/soceng_session_id.txt', 'w')
    soceng_session.write('0')
    soceng_session.close

    msg_limit_file = open(f'log/tmp_soceng_send.txt', 'w')
    msg_limit_file.write('')
    msg_limit_file.close

    msg_limit_dialogue_file = open(f'log/tmp_dialogue_send.txt', 'w')
    msg_limit_dialogue_file.write('')
    msg_limit_dialogue_file.close

    # browser is now ready with QR code.
    # let's wait someone to scan this QR in WA application and start a new session
    return JsonResponse({
        'instance': session_id
    })


@csrf_exempt
def delete_instance(request, instance_id):
    if request.method == 'DELETE':
        instance = active_sessions.pop(instance_id, None)
        logging.getLogger("info").info("instance {instance} deleted".format(instance=instance))
        response = {
            'status': 'success',
            'message': 'instance {instance} deleted successfully'.format(instance=instance_id)
        }
        return HttpResponse(json.dumps(response), headers=headers, status=200)
    else:
        return HttpResponse(status=405)


def send_message(data):
    instance = data.get('instance', '')
    instance = instance.strip()
    if not instance:
        print('no instance found')
        return HttpResponse(
            json.dumps({
                'message': 'no instance found'
            }), headers=headers, status=400
        )

    phone = data.get('phone', '')
    phone = phone.strip('+')
    if not phone:
        print('no phone found')
        return HttpResponse(
            json.dumps({
                'message': 'no phone found'
            }), headers=headers, status=400
        )

    message = data.get('message', '')
    message = message.strip()
    if not message:
        print('no message found')
        return HttpResponse(
            json.dumps({
                'message': 'no message found'
            }), headers=headers, status=400
        )

    browser = active_sessions.get(instance, None)
    if not browser:
        print('no active instance found')
        return HttpResponse(
            json.dumps({
                'message': f'no active instance with instance id {instance} found'.format(instance=instance)
            }), headers=headers, status=400
        )

    # open chat URL to this number and wait for window/chats to load
    browser.get(CHAT_URL.format(phone=phone))

    time.sleep(3)

    # find text input box
    try:
        input_box = WebDriverWait(browser, 180).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
        )
    except Exception:
        logger.error(f"Error timeout error for page to load chat from {phone}.")
        return HttpResponse(
            json.dumps({
                'message': f'Error timeout error for page to load chat from {phone}.'.format(phone=phone)
            }), headers=headers, status=400
        )

    for line in message.splitlines():
        stoppage_line = random.randint(10, 20)
        logger.info(f'Send Message pause every {stoppage_line} character')
        for idx, word in enumerate(line):
            if ((idx+1) % stoppage_line) == 0:
                time.sleep(random.randint(5, 10))
            input_box.send_keys(word)
            time.sleep(.3)
        #input_box.send_keys(line)
        input_box.send_keys(Keys.SHIFT, Keys.ENTER)

    time.sleep(5)

    input_box.send_keys(Keys.ENTER)

    logger.info(f"Message sent successfully to {phone}")
    return HttpResponse(
        json.dumps({
            'status': 'success',
            'message': 'Message sent successfully to {phone}'.format(phone=phone)
        }),
        headers=headers,
        status=200
    )


@csrf_exempt
def send(request):
    if request.method == 'GET':
        print(request.GET)
        data = request.GET
        return send_message(data)

    if request.method == 'POST':
        data = request.body  # byte
        data = json.loads(data.decode('utf-8'))  # json/dict
        return send_message(data)

    else:
        return HttpResponse(status=405)

@csrf_exempt
def check_number(request):
    if request.method == 'POST':
        data = request.POST
        files = request.FILES

        instance = data.get('instance', '')
        instance = instance.strip()
        if not instance:
            logger.warning('Instance browser is empty.')
            print('No instance found')

            del instance

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'Instance is required'
                }), headers=headers, status=400
            )

        # get driver browser from instance id
        browser = active_sessions.get(instance, None)
        if not browser:
            logger.error(f'No active instance browser {instance} found.')
            print('No active instance found')

            del browser

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': f'No active instance with instance id {instance} found'.format(instance=instance)
                }), headers=headers, status=400
            )

        # default start interval random value is 10800s (3h)
        start_interval = 10800
        start_value = data.get('start_interval', '')
        start_value = start_value.strip()
        if start_value:
            start_interval = int(start_value)

        # default end interval random value is 18000s (5h)
        end_interval = 18000
        end_value = data.get('end_interval', '')
        end_value = end_value.strip()
        if end_value:
            end_interval = int(end_value)

        # default total message of interval is 400
        total_number = 900
        message_count = data.get('total_number_interval', '')
        message_count = message_count.strip()
        if message_count:
            total_number = int(message_count)

        # default timeout is 300s
        timeout = 300
        timeout_interval = data.get('timeout', '')
        timeout_interval = timeout_interval.strip()
        if timeout_interval:
            timeout = int(timeout_interval)

        handles = len(browser.window_handles)
        if handles == 1:
            # open new tab
            Browser.new_tab(browser)

        # read phone number file
        files = excel.read_file(files['file'])

        logger.info(f"""start_interval: {start_interval}, end_interval: {end_interval},
                    total_limit_phone: {total_number} timeout: {timeout_interval}""")

        print('\nStart processing bulk check number whatsapp...')
        logger.info('Start processing bulk check number whatsapp.')

        # iterate the target number in array phone list
        for index, phone in files.itertuples(index=True):
            data_report = [tools.get_datetime('%Y-%m-%d')]
            time_start = time.perf_counter()
            print(f'\n{tools.get_datetime("%d-%m-%Y %H:%M:%S")}')
            print(f'{index + 1}. Processing check phone number {phone}')
            logger.info(f'{index + 1}. Processing check phone number {phone}')

            report_time_start = tools.get_datetime('%H:%M:%S')
            # check format phone number
            phone = str(phone)
            phone = phone.strip()
            phone_number = check_format_number(phone)
            # skip if result from check_format_number is empty
            if not phone_number:
                report_time_stop = tools.get_datetime('%H:%M:%S')
                invalid_no_message = f'Incorrect format mobile phone number: {phone}'
                print(f'----| {invalid_no_message}')
                logger.error(f'{invalid_no_message}')
                data_report.extend([report_time_start, report_time_stop, phone, 'Error', invalid_no_message, ''])

                # write invalid phone number to excel
                file_invalid_number = f'./report/check_number/invalid/invalid_number_{current_date}.xlsx'
                insert_excel(data_report, file_invalid_number)
                data_report.clear()

                del report_time_start, report_time_stop, invalid_no_message, file_invalid_number, phone_number, phone
                # skip current iteration
                continue

            # change the user-agent browser for each request
            # ua = tools.random_ua()
            # browser.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua})
            # logger.info(f'User agent: {ua}')

            # open chat URL to this number and wait for window/chats to load
            browser.get(CHAT_URL.format(phone=phone_number))

            # wait until page is loaded
            is_timeout = False
            try:
                WebDriverWait(browser, timeout).until(lambda driver: (
                    element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
                ))
            except Exception:
                is_timeout = True
                report_time_stop = tools.get_datetime('%H:%M:%S')
                timeout_msg = f'Timeout error waiting for page to load to check phone number {phone_number}.'
                print(f'----| {timeout_msg}')
                logger.error(f'{timeout_msg}.')
                data_report.extend([report_time_start, report_time_stop, phone, 'Error', timeout_msg, ''])

            if is_timeout:
                # write timeout phone number to excel
                file_timeout_number = f'./report/check_number/timeout/timeout_check_{current_date}.xlsx'
                insert_excel(data_report, file_timeout_number)
                data_report.clear()

                del time_start, file_timeout_number, is_timeout, report_time_start, report_time_stop, timeout_msg, phone_number, phone
                # skip current iteration when timeout
                continue

            time.sleep(random.randint(7, 12))

            # verify the existence of a phone number on Whatsapp
            number_exists = True
            try:
                browser.find_element(By.CSS_SELECTOR, Selectors.CONVERSATION_PANEL)
            except NoSuchElementException:
                number_exists = False

            if not number_exists:
                report_time_stop = tools.get_datetime('%H:%M:%S')
                not_exist_msg = f'Phone number {phone_number} is not exist on whatsapp or invalid'
                print(f'----| {not_exist_msg}')
                logger.error(f'{not_exist_msg}.')
                data_report.extend([report_time_start, report_time_stop, phone, 'Error', not_exist_msg, ''])

                # write invalid phone number to excel
                file_invalid_number = f'./report/check_number/invalid/invalid_number_{current_date}.xlsx'
                insert_excel(data_report, file_invalid_number)
                data_report.clear()

                del file_invalid_number, not_exist_msg

                # close pop up information phone number is invalid
                # try:
                #     popup = WebDriverWait(browser, timeout).until(
                #         EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.POPUP_CONFIRM))
                #     )
                #     time.sleep(3)
                #     popup.click()
                # except NoSuchElementException:
                #     logger.debug(f'Unable to close pop up error invalid phone number {phone_number} on whatsapp')

            else:
                report_time_stop = tools.get_datetime('%H:%M:%S')
                valid_no_msg = f'Phone number {phone_number} is valid'
                print(valid_no_msg)
                logger.info(valid_no_msg)
                data_report.extend([report_time_start, report_time_stop, phone, 'Success', valid_no_msg, ''])

                # write valid phone number to excel
                file_valid_number = f'./report/check_number/valid/valid_number_{current_date}.xlsx'
                insert_excel(data_report, file_valid_number)
                data_report.clear()

                del file_valid_number, valid_no_msg

            del is_timeout, number_exists, report_time_start, report_time_stop
            time.sleep(1)

            # close conversation panel
            browser.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)

            # set interval time after reaching of total phone numbers
            if index % total_number == 0 and index > 0:
                interval = random.randint(start_interval, end_interval)
                print(f'----| Wait for {interval}s to check the next number')
                items = list(range(interval, 0, -1))
                del interval

                print('\n\n')
                for item in countdown(items, prefix = 'Next check number in:'):
                    time.sleep(1)

                del items

            else:
                random_number = random.randint(3, 6)
                print(f'----| Rest in {random_number}s')
                time.sleep(random_number)
                del random_number

            # measure mobile number checkting time
            time_end = time.perf_counter() - time_start
            print(f'----| It takes {time_end:.2f}s to check phone number')

            del time_start, time_end

        if handles > 1:
            Browser.close_tab(browser)

        del data, files, instance, browser, phone, index, start_interval, start_value, end_interval, end_value
        del total_number, message_count, timeout, timeout_interval, handles
        logger.info(f'Successfully check phone number list')
        print('\nSuccessfully check phone number list\n')
        return HttpResponse(
            json.dumps({
                'status': 'success',
                'message': 'Successfully check phone number list'
            }),
            headers=headers,
            status=200
        )

    else:
        return HttpResponse(status=405)

@csrf_exempt
def bulk_send(request):
    if request.method == 'POST':
        data = request.POST
        files = request.FILES
        blast_file = files['file']
        if not blast_file:
            logger.warning('List phone number is empty')
            print('List phone number is empty')

            del blast_file

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'List phone number is required'
                }), headers=headers, status=400
            )

        soceng_file = files['soceng_file']
        if not soceng_file:
            logger.warning('File social engineering is empty')
            print('File social engineering is empty')

            del soceng_file

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'File social engineering is required'
                }), headers=headers, status=400
            )

        dialogue_file = files['dialogue_file']
        message_file = files['message_file']
        if not message_file:
            logger.warning('List blast message is empty')
            print('List blast message is empty')

            del dialogue_file, message_file

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'List blast message is required'
                }), headers=headers, status=400
            )

        instance = data.get('instance', '')
        instance = instance.strip()
        if not instance:
            logger.warning('Instance browser is empty.')
            print('No instance found')

            del instance

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'Instance is required'
                }), headers=headers, status=400
            )

        # get driver browser from instance id
        browser = active_sessions.get(instance, None)
        if not browser:
            logger.error(f'No active instance browser {instance} found.')
            print('No active instance found')

            del browser

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': f'No active instance with instance id {instance} found'.format(instance=instance)
                }), headers=headers, status=400
            )

        # message = data.get('message', '')
        # message = message.strip()
        # if not message:
            # logger.warning('Message whatsapp is empty.')
            # print('Message whatsapp is empty')

            # return HttpResponse(
            #     json.dumps({
            #         'status': 'error',
            #         'message': 'Message is required'
            #     }), headers=headers, status=400
            # )

        # default start interval random value is 10800s (3h)
        start_interval = 10800
        start_value = data.get('start_interval', '')
        start_value = start_value.strip()
        if start_value:
            start_interval = int(start_value)

        # default end interval random value is 18000s (5h)
        end_interval = 18000
        end_value = data.get('end_interval', '')
        end_value = end_value.strip()
        if end_value:
            end_interval = int(end_value)

        # default random value for start interval dialogue is 300s (5m)
        dialogue_start_interval = 300
        dialogue_start = data.get('dialogue_start_interval', '')
        dialogue_start = dialogue_start.strip()
        if dialogue_start:
            dialogue_start_interval = int(dialogue_start)

        # default random value for end interval dialogue is 900s (15m)
        dialogue_end_interval = 900
        dialogue_end = data.get('dialogue_end_interval', '')
        dialogue_end = dialogue_end.strip()
        if dialogue_end:
            dialogue_end_interval = int(dialogue_end)

        # default random value for start interval soceng is 6s
        soceng_start_interval = 6
        soceng_start = data.get('soceng_start_interval', '')
        soceng_start = soceng_start.strip()
        if soceng_start:
            soceng_start_interval = int(soceng_start)

        # default random value for end interval dialogue is 12s
        soceng_end_interval = 12
        soceng_end = data.get('soceng_end_interval', '')
        soceng_end = soceng_end.strip()
        if soceng_end:
            soceng_end_interval = int(soceng_end)

        # default total message of interval is 400
        total_message = 400
        message_count = data.get('total_message_interval', '')
        message_count = message_count.strip()
        if message_count:
            total_message = int(message_count)

        # default timeout is 300s
        timeout = 300
        timeout_interval = data.get('timeout', '')
        timeout_interval = timeout_interval.strip()
        if timeout_interval:
            timeout = int(timeout_interval)

        browser.switch_to.window(browser.window_handles[0])
        handles = browser.window_handles
        for _, handle in enumerate(handles):
            if handle != browser.current_window_handle:
                browser.switch_to.window(handle)
                browser.close()

        browser.switch_to.window(browser.window_handles[0])
        event = Event()

        # total_message_send = data.get('total_message_send')
        # total_message_send = total_message_send.strip()
        message_index = 0
        # if not total_message_send:
        #     total_message_send = 0

        # total_message_send = int(total_message_send)

        # limit message wa
        message_limit = 0
        total_message_limit_first = 900
        total_message_limit_last = 999
        random_message_limit = random.randint(total_message_limit_first, total_message_limit_last)

        msg_limit_file = open(f'log/tmp_message_limit.txt', 'w')
        msg_limit_file.write(str(0))
        msg_limit_file.close

        # read phone number file
        files = excel.read_file(blast_file)

        logger.info(f"""start_interval: {start_interval}, end_interval: {end_interval},
                    dialogue_start_interval: {dialogue_start_interval}, dialogue_end_interval: {dialogue_end_interval},
                    total_message: {total_message}, timeout: {timeout_interval}""")

        print('\nStart processing bulk send whatsapp...')
        logger.info('Start processing bulk send whatsapp.')
        # iterate the target number in array phone list
        for index, phone in files.itertuples(index=True):
            data_report = [tools.get_datetime('%Y-%m-%d')]
            time_start = time.perf_counter()

            msg_limit_file = open(f'log/tmp_message_limit.txt', 'r')
            tmp_msg_limit = msg_limit_file.read()
            msg_limit_file.close

            # set default tmp_msg_limit to message_limit if msg_limit_file is empty
            if not tmp_msg_limit:
                tmp_msg_limit = message_limit

            message_limit = int(tmp_msg_limit)

            # stop blast message when process send message reach random_message_limit
            if message_limit == random_message_limit or message_limit > random_message_limit:
                print(f'----| Total message limit is reached {random_message_limit}')
                logger.info(f'Total message limit is reached {random_message_limit}')

                del data_report, time_start, msg_limit_file, tmp_msg_limit, message_limit
                break

            print(f'\n{tools.get_datetime("%d-%m-%Y %H:%M:%S")}')
            print(f'{index + 1}. Trying to send message to {phone}')
            logger.info(f'{index + 1}. Trying to send message to {phone}')

            report_time_start = tools.get_datetime('%H:%M:%S')
            # check format phone number
            phone = str(phone)
            phone = phone.strip()
            phone_number = check_format_number(phone)
            report_time_stop = tools.get_datetime('%H:%M:%S')
            # skip iteration if result from check_format_number is empty
            if not phone_number:
                invalid_no_message = f'Incorrect format mobile phone number: {phone}'
                print(invalid_no_message)
                logger.error(invalid_no_message)
                data_report.extend([report_time_start, report_time_stop, phone, 'Error', invalid_no_message, ''])

                # write failed send message phone number to excel
                failed_number = f'./report/send/failed/failed_send_{current_date}.xlsx'
                insert_excel(data_report, failed_number)
                data_report.clear()

                del time_start, failed_number
                # skip current iteration
                continue

            if event.is_set():
                Browser.close_tab(browser)

            handles = len(browser.window_handles)
            if handles == 1:
                # open new tab
                Browser.new_tab(browser)

            # change the user-agent browser for each request
            # ua = tools.random_ua()
            # browser.execute_cdp_cmd('Network.setUserAgentOverride', {'userAgent': ua})
            # logger.info(f'User agent: {ua}')

            # open chat URL to this number and wait for window/chats to load
            browser.get(CHAT_URL.format(phone=phone_number))
            time.sleep(6)

            # check if the page is loaded
            try:
                WebDriverWait(browser, timeout).until(lambda driver: (
                    element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
                ))
            except TimeoutException:
                report_time_stop = tools.get_datetime('%H:%M:%S')
                timeout_msg = f'Timeout error waiting for page to load chat from {phone_number}.'
                logger.error(timeout_msg)
                print(f'----| {timeout_msg}')
                data_report.extend([report_time_start, report_time_stop, phone, 'Error', timeout_msg, ''])

                # write timeout phone number to excel
                file_timeout_number = f'./report/send/timeout/timeout_send_{current_date}.xlsx'
                insert_excel(data_report, file_timeout_number)
                data_report.clear()

                del file_timeout_number
                # skip current iteration when timeout
                continue

            time.sleep(3)

            # dynamic blast message
            message_list = pd.read_excel(message_file, index_col=None, header=None)
            df_message = pd.DataFrame(message_list)
            # get next message
            if index + 1 > 1 and total_message > 0:
                message_index = message_index + 1

            # reset message to beginning
            if message_index >= len(df_message):
                message_index = 0

            message = df_message[0][message_index]

            is_success = True
            try:
                # find text input box
                input_box = WebDriverWait(browser, 120).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
                )
                logger.info(f'Message blast: {message}.')
                print(f'Message blast: {message}.')
                paste_text(browser, input_box, message)

                time.sleep(10)

                # send message by press Enter
                input_box.send_keys(Keys.ENTER)
                report_time_stop = tools.get_datetime('%H:%M:%S')

                del input_box, message_list, df_message

                time.sleep(random.randint(4, 7))
            except Exception:
                is_success = False
                failed_sending_msg = f'Failed send message to {phone_number}.'
                logger.error(failed_sending_msg)
                print(f'----| {failed_sending_msg}')
                data_report.extend([report_time_start, report_time_stop, phone, 'Error', failed_sending_msg, ''])

                # write failed send message phone number to excel
                failed_number = f'./report/send/failed/failed_send_{current_date}.xlsx'
                insert_excel(data_report, failed_number)
                data_report.clear()

                del failed_number
                # skip current iteration
                continue

            if is_success:
                success_sending_msg = f'Successfully sending message to {phone_number}'
                print(f'----| {success_sending_msg}')
                logger.info(success_sending_msg)
                data_report.extend([report_time_start, report_time_stop, phone, 'Success', success_sending_msg, message])
                del success_sending_msg

                # write timeout phone number to excel
                success_number = f'./report/send/success/success_send_{current_date}.xlsx'
                insert_excel(data_report, success_number)
                data_report.clear()

                message_limit = message_limit + 1
                msg_limit_file = open(f'log/tmp_message_limit.txt', 'w')
                msg_limit_file.write(str(message_limit))
                msg_limit_file.close
                del success_number

                msg_limit_file = open(f'log/tmp_message_limit.txt', 'r')
                tmp_msg_limit = msg_limit_file.read()
                msg_limit_file.close
                del msg_limit_file, tmp_msg_limit, data_report, report_time_start, report_time_stop, phone

            # measure sending message time
            time_end = time.perf_counter() - time_start
            print(f'----| It takes {time_end:.2f}s for sending message to {phone_number}')
            del time_start, time_end, phone_number, message

            # close tab
            Browser.close_tab(browser)

            # set interval time after reaching of total messages
            if index % total_message == 0 and index > 0:
                # delete the group chat before the social engineering process program begins
                threads_group_chat = Thread(target=clear_chat, args=(browser,))
                threads_group_chat.start()
                # wait for thread clear group chat to finish
                threads_group_chat.join()
                del threads_group_chat

                interval = random.randint(start_interval, end_interval)
                print(f'----| Wait for {interval}s to send the next message')
                items = list(range(interval, 0, -1))

                threads = Thread(target=dialogue, args=(browser, dialogue_file, dialogue_start_interval, dialogue_end_interval, timeout, event, message_limit, random_message_limit, 'dialogue'))
                threads.start()

                print('\n\n')
                for item in countdown(items, prefix = 'Next blast message in:'):
                    time.sleep(1)

                del items

                # stop dialogue chat when no interval blast message
                event.set()
                # wait for new thread to finish
                threads.join()
                # reset event to false
                event.clear()

            else:
                # start social engineering
                threads = Thread(target=dialogue, args=(browser, soceng_file, soceng_start_interval, soceng_end_interval, timeout, event, message_limit, random_message_limit, 'soceng'))
                threads.start()

                random_number = random.randint(5, 8)
                print(f'----| Rest in {random_number}s')
                time.sleep(random_number)

                # stop social engineering when program interval blast message is complete
                event.set()
                # wait for new thread to finish
                threads.join()
                # reset event to false
                event.clear()
                del random_number

            del is_success, threads

        # Check reply message
        handles = len(browser.window_handles)
        if handles > 1:
            Browser.close_tab(browser)

        Browser.new_tab(browser)
        browser.get(BASE_URL)
        try:
            WebDriverWait(browser, 10).until(lambda driver: (
                element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
            ))
            time.sleep(3)

            reply_message(browser)
        except Exception:
            print('Failed to get data reply message')

        del data, files, instance, handles, browser, phone, index
        logger.info('Successfully sending bulk message')
        print('\nSuccessfully sending bulk message\n')
        return HttpResponse(
            json.dumps({
                'status': 'success',
                'message': 'Bulk message sent successfully'
            }),
            headers=headers,
            status=200
        )

    else:
        return HttpResponse(status=405)


@csrf_exempt
def remove_duplicate_number(request):
    if request.method == 'POST':
        data = request.POST
        files = request.FILES
        phone_file = files['file']

        if not phone_file:
            logger.warning('File list phone number is empty.')
            print('File list phone number excel is empty')

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'File is required'
                }), headers=headers, status=400
            )

        output_file = data.get('output_file_location', '')
        output_file = output_file.strip()
        if not output_file:
            logger.warning('Output file location is empty.')
            print('Output file location is empty')

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'Output file location is required'
                }), headers=headers, status=400
            )

        # read phone number file
        data = pd.read_excel(phone_file)
        df = pd.DataFrame(data)

        # get column index in phone list
        column = map(str, df.columns)
        data_list = list(column)
        df2 = pd.DataFrame([data_list], columns=[i for i in df])

        # insert column index name in phone number file to new array phone list
        phone_list = pd.concat([df2, df], ignore_index=True)
        phones = pd.DataFrame(phone_list)

        # drop all duplicate data
        duplicates = phones.drop_duplicates(keep='first')
        # delete row index 0
        phone_number = duplicates.drop(index=0)

        # create new file
        folder = Folder()

        file_path = path.expanduser(output_file)
        is_exists = folder.is_exists(file_path)
        if not is_exists:
            # create directory if not exist
            folder.mkdir(file_path)

        phone_number.to_excel(output_file, index=False)

        print('\nSuccessfully remove duplication phone number file\n')
        return HttpResponse(
            json.dumps({
                'status': 'success',
                'message': 'Successfully remove duplication phone number file'
            }),
            headers=headers,
            status=200
        )
    else:
        return HttpResponse(status=405)

def insert_excel(data, file_path):
    # get file name excel
    filename = file_path.split('/')
    filename = filename[-1]
    # get how many row number in file excel
    row_number = excel.count_row(file_path)
    # save data to excel
    excel.append_data(data, file_path, row_number)

    # print(f'Successfully insert data to excel {filename}')
    logging.getLogger('info').info(f'Successfully insert data to excel {filename}')

    del filename, row_number

def dialogue(browser, file_path, start_interval, end_interval, timeout, event, message_limit, random_message_limit, chat_type = 'dialogue'):
    if not file_path:
        print(f'\nFile excel for {chat_type} is not found')
        logger.info(f'File excel for {chat_type} is not found.')
        del chat_type

        return None

    time.sleep(1)

    handles = len(browser.window_handles)
    if handles == 1:
        # open new tab
        Browser.new_tab(browser)

    # read phone number file
    files = excel.read_file(file_path)
    total_message = len(files)

    print(f'\n\n\nStart processing {chat_type}...')
    logger.info(f'Start processing {chat_type}')

    idx_dialogue = 0
    # iterate the target number in array phone list
    for index, phone, message in files.itertuples(index=True):
        msg_limit_file = open(f'log/tmp_message_limit.txt', 'r')
        tmp_msg_limit = msg_limit_file.read()
        msg_limit_file.close

        # set default tmp_msg_limit to message_limit if msg_limit_file2 is empty
        if not tmp_msg_limit or int(tmp_msg_limit) == 0:
            tmp_msg_limit = message_limit

        msg_limit = int(tmp_msg_limit)

        # stop soceng when process total sending message reach random_message_limit
        if msg_limit == random_message_limit or int(idx_dialogue) == 4:
            idx_dialogue = 0
            print(f'----| Total message limit {chat_type} is reached')
            logger.info(f'Total message limit {chat_type} is reached')

            del msg_limit_file, tmp_msg_limit, msg_limit, idx_dialogue

            break

        #  open and read session index soceng to continue the process
        dialoge_session = open(f'log/{chat_type}_session_id.txt', 'r')

        # check if the event is set
        if event.is_set():
            dialoge_session.close

            # if the event is set then stop soceng process
            break

        # read file session index soceng
        idx = dialoge_session.read()
        dialoge_session.close

        # set default idx to 0
        if not idx or int(idx) >= total_message:
            idx = 0

        # if current index is less or equal to session index then skip iteration
        if index < int(idx):
            del idx
            continue

        # write session index for soceng
        session_id = open(f'log/{chat_type}_session_id.txt', 'w')
        session_id.write(str(index + 1))
        session_id.close

        del session_id

        time_start = time.perf_counter()
        print(f'\n{tools.get_datetime("%d-%m-%Y %H:%M:%S")}')
        print(f'{index + 1}. Trying to {chat_type} with number {phone}')
        logger.info(f'{index + 1}. Trying to {chat_type} with number {phone}')

        handles = len(browser.window_handles)
        if handles == 1:
            # open new tab
            Browser.new_tab(browser)

        data_report = [tools.get_datetime('%Y-%m-%d')]
        report_time_start = tools.get_datetime('%H:%M:%S')

        # check format phone number
        phone = str(phone)
        phone = phone.strip()
        phone_number = check_format_number(phone)
        # skip iteration if result from check_format_number is empty
        if not phone_number:
            report_time_stop = tools.get_datetime('%H:%M:%S')
            incorrect_no_msg = f'Incorrect format mobile phone number: {phone}.'
            print(incorrect_no_msg)
            logger.error(incorrect_no_msg)
            data_report.extend([report_time_start, report_time_stop, phone, 'Error', incorrect_no_msg, ''])

            # write invalid phone number to excel
            file_invalid_number = f'./report/{chat_type}/invalid/invalid_number_{chat_type}_{current_date}.xlsx'
            insert_excel(data_report, file_invalid_number)
            data_report.clear()

            del time_start, file_invalid_number, report_time_stop, incorrect_no_msg, phone_number, phone, handles
            # skip current iteration
            continue

        # open chat URL to this number and wait for window/chats to load
        browser.get(CHAT_URL.format(phone=phone_number))
        time.sleep(3)

        try:
            WebDriverWait(browser, timeout).until(lambda driver: (
                element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
            ))
        except TimeoutException:
            report_time_stop = tools.get_datetime('%H:%M:%S')
            timeout_msg = f'Timeout error waiting for page to load chat.'
            print(timeout_msg)
            logger.error(timeout_msg)
            data_report.extend([report_time_start, report_time_stop, phone, 'Error', timeout_msg, ''])

            # write timeout phone number to excel
            file_timeout_number = f'./report/{chat_type}/timeout/timeout_{chat_type}_{current_date}.xlsx'
            insert_excel(data_report, file_timeout_number)
            data_report.clear()

            del report_time_stop, timeout_msg, file_timeout_number, phone_number, phone, handles
            # skip current iteration when timeout
            continue

        time.sleep(3)
        is_success = True
        # Check conversation header to identify phone number is valid
        try:
            lang_element = browser.find_element(By.CSS_SELECTOR, 'html').get_attribute('lang')
            logger.info(f'HTML lang attribute: {lang_element}')

            conv_header = Selectors.CONVERSATION_HEADER_ID if lang_element == 'id' else Selectors.CONVERSATION_HEADER

            browser.find_element(By.CSS_SELECTOR, conv_header)
        except NoSuchElementException:
            is_success = False
            invalid_no_msg = f'Phone number {phone} is invalid'
            print(invalid_no_msg)
            logger.error(invalid_no_msg)
            del invalid_no_msg

        except Exception:
            is_success = False
            exception_msg = 'Error when trying to check conversation header'
            print(exception_msg)
            logger.error(exception_msg)
            del exception_msg

        if not is_success:
            try:
                WebDriverWait(browser, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.POPUP))
                )
                # browser.find_element(By.CSS_SELECTOR, Selectors.POPUP_CONFIRM).click()
            except TimeoutException:
                is_success = True
                timeout_dialoge_msg = f'Timeout when program trying to find popup invalid phone number.'
                print(timeout_dialoge_msg)
                logger.error(timeout_dialoge_msg)
                del timeout_dialoge_msg
            except NoSuchElementException:
                is_success = True
                popup_not_found_msg = 'Error no such element popup invalid phone number'
                print(popup_not_found_msg)
                logger.error(popup_not_found_msg)
                del popup_not_found_msg

            # skip current iteration when timeout
            continue
        else:
            logger.info(f'Message {chat_type}: {message}.')
            print(f'Message {chat_type}: {message}.')
            try:
                # find text input box
                input_box = WebDriverWait(browser, 120).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
                )
                for line in message.splitlines():
                    input_box.send_keys(line)
                    input_box.send_keys(Keys.SHIFT, Keys.ENTER)

                time.sleep(9)

                # send message by press Enter
                input_box.send_keys(Keys.ENTER)
                report_time_stop = tools.get_datetime('%H:%M:%S')

                del input_box

                # write temp count message limit
                message_limit = message_limit + 1
                tmp_message_limit = open(f'log/tmp_message_limit.txt', 'w')
                tmp_message_limit.write(str(message_limit))
                tmp_message_limit.close
                del tmp_message_limit

                idx_dialogue = idx_dialogue + 1

                time.sleep(5)
                # close tab
                Browser.close_tab(browser)
            except Exception:
                failed_sending_msg = f'Failed to {chat_type} with {phone_number}'
                print(failed_sending_msg)
                logger.error(failed_sending_msg)
                report_time_stop = tools.get_datetime('%H:%M:%S')
                data_report.extend([report_time_start, report_time_stop, phone, 'Error', failed_sending_msg, ''])

                # write failed send message phone number to excel
                failed_number = f'./report/{chat_type}/failed/failed_{chat_type}_{current_date}.xlsx'
                insert_excel(data_report, failed_number)
                data_report.clear()

                del failed_number, failed_sending_msg, report_time_start, report_time_stop, phone_number, phone
                # skip current iteration
                continue

        if is_success or not event.is_set():
            success_sending_msg = f'Successfully {chat_type} chat with {phone_number}'
            print(f'----| {success_sending_msg}')
            logger.info(success_sending_msg)
            data_report.extend([report_time_start, report_time_stop, phone, 'Error', success_sending_msg, message])

            # write success dialogue chat to excel
            success_number = f'./report/{chat_type}/send/success_send_{current_date}.xlsx'
            insert_excel(data_report, success_number)
            data_report.clear()
            del success_number, success_sending_msg

        # measure dialogue time
        time_end = time.perf_counter() - time_start
        print(f'----| It takes {time_end:.2f}s for {chat_type} with {phone_number}')
        del time_start, time_end, is_success, phone_number, phone, handles, data_report, report_time_start, report_time_stop, msg_limit

        random_number = random.randint(start_interval, end_interval)
        print(f'\r----| Rest in {random_number}s\n')
        print('')
        time.sleep(random_number)
        del random_number

    print(f'\nProcessing {chat_type} is done\n')
    logger.info(f'Processing {chat_type} is done')
    del start_interval, end_interval, chat_type

def clear_group_chat(data):
    if data.method == 'GET':
        data = data.GET
        instance = data.get('instance', '')

    instance = instance.strip()
    if not instance:
        print('no instance found')
        return HttpResponse(
            json.dumps({
                'message': 'no instance found'
            }), headers=headers, status=400
        )

    browser = active_sessions.get(instance, None)
    if not browser:
        print('no active instance found')
        return HttpResponse(
            json.dumps({
                'message': f'no active instance with instance id {instance} found'.format(instance=instance)
            }), headers=headers, status=400
        )

    clear_all_group_chat(browser)

    logger.info("Group chat is successfully deleted")
    return HttpResponse(
        json.dumps({
            'status': 'success',
            'message': 'Group chat is successfully deleted'
        }),
        headers=headers,
        status=200
    )

def clear_all_group_chat(browser):
    handles = len(browser.window_handles)
    if handles == 1:
        # open new tab
        Browser.new_tab(browser)

        # open chat URL and wait for window/chats to load
        browser.get(BASE_URL)

    time.sleep(3)
    is_loaded = True
    try:
        WebDriverWait(browser, 30).until(lambda driver: (
            element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
        ))
    except TimeoutException:
        is_loaded = False
        logger.error(f'Timeout error to clear chat.')
        print(f'Timeout error to clear chat')

    time.sleep(1)

    if is_loaded:
        lang_element = browser.find_element(By.CSS_SELECTOR, 'html').get_attribute('lang')
        logger.info(f'This WhatsApp web uses language: {lang_element}')
        conv_header = Selectors.CONVERSATION_HEADER_ID if lang_element == 'id' else Selectors.CONVERSATION_HEADER
        unread_notif_chat = Selectors.UNREAD_CONVERSATIONS_ID if lang_element == 'id' else Selectors.UNREAD_CONVERSATIONS

        chats = browser.find_elements(By.CSS_SELECTOR, unread_notif_chat)
        if chats:
            for chat in chats:
                try:
                    # click detail chat
                    chat.click()
                except Exception as e:
                    logger.error('Error when program to click the chat. Error: {e}'.format(e=e))
                    print('Error when program to click the chat')

                # open the chat info
                try:
                    WebDriverWait(browser, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, conv_header))
                    )
                    browser.find_element(By.CSS_SELECTOR, conv_header).click()
                except TimeoutException:
                    logger.error('Timeout error to open the chat info.')
                    print('Timeout error to open the chat info')
                except NoSuchElementException:
                    logger.error('Error no such element conversation header')
                    print('Error no such element conversation header')

                time.sleep(1)
                is_group_chat = True
                try:
                    browser.find_element(By.CSS_SELECTOR, Selectors.GROUP_INFO_HEADER)
                except NoSuchElementException:
                    is_group_chat = False

                if is_group_chat:
                    # group subject
                    group_subject = browser.find_element(By.CSS_SELECTOR, Selectors.GROUP_SUBJECT)
                    logger.info(f'Clear group chat {group_subject.text}')
                    print(f'-> {group_subject.text}')

                    # clear chat group
                    clear_chat(browser)
                else:
                    # change badge to unread
                    try:
                        actions = ActionChains(browser)
                        actions.context_click(chat).perform()
                        time.sleep(2)

                        browser.find_element(By.CSS_SELECTOR, '#app > div ul > div > li:nth-child(5) > div').click()
                    except Exception as e:
                        logger.error('Error when program to right click the chat for change badge unread. Error: {e}'.format(e=e))
                        print('Error when program to change badge unread chat. Error: {e}'.format(e=e))

    # Close tab
    if handles > 1:
        Browser.close_tab(browser)

def clear_chat(browser):
    lang_element = browser.find_element(By.CSS_SELECTOR, 'html').get_attribute('lang')
    menu_clear_selector = Selectors.MENU_CLEAR_ID if lang_element == 'id' else Selectors.MENU_CLEAR

    try:
        print('Trying to clear chat')
        logger.info('Trying to clear chat')
        time.sleep(0.5)

        # Wait for the GROUP_BUTTON_MENU element to be clickable
        WebDriverWait(browser, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, Selectors.GROUP_BUTTON_MENU))
        )
        browser.find_element(By.CSS_SELECTOR, Selectors.GROUP_BUTTON_MENU).click()
        time.sleep(1)
        print('Click dropdown menu')
        logger.info('Click dropdown menu')

        # Wait for the menu_clear_selector element to be clickable
        WebDriverWait(browser, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, menu_clear_selector))
        )
        browser.find_element(By.CSS_SELECTOR, menu_clear_selector).click()
        time.sleep(1)
        print('Click clear chat menu')
        logger.info('Click clear chat menu')

        # Wait for the POPUP_CONFIRM element to be clickable
        WebDriverWait(browser, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, Selectors.POPUP_CONFIRM))
        )
        browser.find_element(By.CSS_SELECTOR, Selectors.POPUP_CONFIRM).click()
        print('Click confirm button')
        print('\n')
        logger.info('Click confirm button')
        time.sleep(1)

        print(f'\nClear chat processing is complete\n')
        logger.info(f'Clear chat processing is complete')
    except NoSuchElementException as e:
        print('Clear chat menu is not found')
        logger.error('Clear chat menu is not found. Error: {e}'.format(e=e))
    except Exception as e:
        print('Failed to clear chat')
        logger.error('Failed to clear chat. Error: {e}'.format(e=e))

def get_reply_message(data):
    data = data.GET
    instance = data.get('instance', '')
    instance = instance.strip()

    browser = active_sessions.get(instance, None)
    WebDriverWait(browser, 10).until(lambda driver: (
        element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
    ))
    time.sleep(2)

    logger.info('Trying to get a reply message')
    print('Trying to get a reply message')

    reply_message(browser)

    logger.info('Process of getting a message reply is complete')
    print('Process of getting a message reply is complete')

    return HttpResponse(
        json.dumps({
            'status': 'success',
            'message': 'Successfully get reply message'
        }),
        headers=headers,
        status=200
    )

def auto_reply_message(browser, input_data, auto_reply_conf=True, type_log_msg=''):
    if auto_reply_conf:
        print(f'\nStart checking reply message {type_log_msg}')
        logger.info(f'Start checking reply message {type_log_msg}')
        # Check reply message
        handles = len(browser.window_handles)
        if handles > 1:
            Browser.close_tab(browser)

        Browser.new_tab(browser)
        browser.get(BASE_URL)
        time.sleep(6)
        try:
            logger.info('Trying to make sure the search bar in home is available')
            print('Trying to make sure the search bar in home is available')
            WebDriverWait(browser, 90).until(lambda driver: (
                element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
            ))
            time.sleep(6)

            reply_message(browser, auto_reply=auto_reply_conf, input_data=input_data)
        except Exception as e:
            logger.error('Failed to get data reply message. Error: {e}'.format(e=e))
            logger.error(traceback.format_exc())
            print('Failed to get data reply message')

            logger.info('Trying to stop the program')
            print('Trying to stop the program')
            sys.tracebacklimit = 0
            sys.exit(1)

        print(f'\nFinish checking reply message {type_log_msg}')
        logger.info(f'Finish checking reply message {type_log_msg}')

def reply_message(browser, auto_reply, input_data):
    lang_element = browser.find_element(By.CSS_SELECTOR, 'html').get_attribute('lang')
    logger.info(f'\nThis WhatsApp web use language: {lang_element}')
    print(f'This WhatsApp web use language: {lang_element}')
    conv_header = Selectors.CONVERSATION_HEADER_ID if lang_element == 'id' else Selectors.CONVERSATION_HEADER
    unread_notif_chat = Selectors.UNREAD_CONVERSATIONS_ID if lang_element == 'id' else Selectors.UNREAD_CONVERSATIONS
    group_element = Selectors.GROUP_INFO_HEADER_ID if lang_element == 'id' else Selectors.GROUP_INFO_HEADER

    #input_data = pd.DataFrame()
    #print('INI INPUT FILE')
    #print(input_file)
    #if input_file:
        # read input file
    #    logger.info('Trying to read input file for auto reply')
    #    print('Trying to read input file for auto reply')
    #    input_data = pd.read_csv(input_file, header=None, names=['message'])
        #print(input_data)
        #print('INPUT DATA BERHASIL')

    print('INI FILE INPUT UTK REPLY MESSAGE')
    print(input_data)
    conversations = browser.find_elements(By.CSS_SELECTOR, unread_notif_chat)
    logger.info(f'Total unread conversations: {len(conversations)}')
    for i in range(len(conversations)):
        data_report = [tools.get_datetime('%Y-%m-%d')]
        report_time_start = tools.get_datetime('%H:%M:%S')

        try:
            # click detail chat
            logger.info(f'{i}. Trying to click the chat')
            print(f'{i}. Trying to click the chat')
            conversations = browser.find_elements(By.CSS_SELECTOR, unread_notif_chat)
            conversations[i].click()
        except Exception as e:
            logger.error('Error when program to click the chat. Error: {e}'.format(e=e))
            logger.error(traceback.format_exc())
            print('Error when program to click the chat')

        try:
            # open the chat info
            logger.info('Trying to open the chat info')
            print('Trying to open the chat info')
            WebDriverWait(browser, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, conv_header))
            )
            browser.find_element(By.CSS_SELECTOR, conv_header).click()
        except TimeoutException:
            logger.error('Timeout error to open the chat info.')
            logger.error(traceback.format_exc())
            print('Timeout error to open the chat info')
        except NoSuchElementException as e:
            logger.error('Error no such element conversation header. Error: {e}'.format(e=e))
            print('Error no such element conversation header')

        time.sleep(5)
        phone=''
        try:
            logger.info('Trying to get phone number')
            print('Trying to get phone number')
            phone_text = browser.find_element(By.CSS_SELECTOR, Selectors.CONTACT_INFO_PHONE).text.strip()
            phone = tools.sanitize_phone_number(phone_text)
            logger.info(f'Phone number: {phone}')
        except NoSuchElementException as e:
            logger.error('Phone text is not found in sidebar')
            print('Phone text is not found in sidebar')
        except Exception as e:
            logger.error('Error when program to get phone number. Error: {e}'.format(e=e))
            logger.error(traceback.format_exc())
            print('Error when program to get phone number')

        valid_phone = check_format_number(phone)
        time.sleep(0.5)
        if not valid_phone:
            try:
                logger.info('Trying to get another phone number info')
                print('Trying to get another phone number info')
                phone_text = browser.find_element(By.CSS_SELECTOR, Selectors.CONTACT_INFO_PHONE2).text.strip()
                phone = tools.sanitize_phone_number(phone_text)
            except NoSuchElementException as e:
                logger.error('Not found phone text. Error: {e}'.format(e=e))
                logger.error(traceback.format_exc())
                print('Not found phone text')
            except Exception as e:
                logger.error('Error when program to get another phone number. Error: {e}'.format(e=e))
                logger.error(traceback.format_exc())
                print('Error when program to get another phone number')

        # close info
        try:
            logger.info('Trying to close header info')
            print('Trying to close header info')
            browser.find_element(By.CSS_SELECTOR, 'header span[data-icon="x"]').click()
        except NoSuchElementException as e:
            logger.error('Failed to close header info. Error: {e}'.format(e=e))
            logger.error(traceback.format_exc())
            print('Failed to close header info')

        group_chat = True
        try:
            # get group info
            logger.info('Trying to get group info')
            print('Trying to get group info')
            browser.find_element(By.CSS_SELECTOR, group_element)
        except NoSuchElementException:
            logger.info('This is not a group chat')
            print('This is not a group chat')
            group_chat = False

        if group_chat:
            # skip current iteration from group chat
            logger.info('Skip current iteration from group chat')
            print('Skip current iteration from group chat')
            continue

        # scroll chat to top
        scroll_chat(browser)
        # get reply message
        data_reply, response = get_data_reply_message(browser)

        success_get_reply = f'Successfully get data reply message from {phone}'
        report_time_stop = tools.get_datetime('%H:%M:%S')
        data_report.extend([report_time_start, report_time_stop, phone, 'Success', success_get_reply, data_reply])

        # write success get data reply message to excel
        file_success = f'./report/reply_message/reply_message_{current_date}.xlsx'
        insert_excel(data_report, file_success)
        logger.info('Successfully write success get reply message to excel')
        print('Successfully write success get reply message to excel')

        # write data reply message to txt file
        file_reply_txt = f'./report/reply_message/reply_message_{current_date}.txt'
        file_txt_folder = Folder.is_exists(file_reply_txt)
        if not file_txt_folder:
            logger.info('Create folder for reply message')
            print('Create folder for reply message')
            Folder.mkdir(file_reply_txt)

        report_file_reply_txt = open(file_reply_txt, 'a')  # append mode
        report_file_reply_txt.write(f'{data_report[0]} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Success | {success_get_reply} | {data_reply}\n')
        report_file_reply_txt.close()
        logger.info('Successfully write data reply message to txt file')
        print('Successfully write data reply message to txt file')

        logger.info(success_get_reply)
        print(success_get_reply)

        # Upload file report to server
        thread = Thread(target=sync_report)
        thread.start()
        thread.join()  # Wait for the thread to finish

        random_message = ['']
        if auto_reply and not input_data.empty and  response:
            try:
                # delete array data in data_report except first data
                data_report = data_report[:1]
                time_start_autoreply = tools.get_datetime('%H:%M:%S')

                print(f'Trying to send auto reply to {phone}')
                logger.info(f'Trying to send auto reply to {phone}')
                print('INI INPUT DATA SAAT SESUAI RESPON')
                print(input_data)
                logger.info('Trying to get random message')
                data_message = input_data['message']
                print('INI DATA MESSAGE')
                print(data_message)
                random_message = random.choice(data_message)
                logger.info(f'Auto reply message: {random_message}')
                print(f'Auto reply message: {random_message}')
            except Exception as e:
                logger.error('Error when program to get random message. Error: {e}'.format(e=e))
                logger.error(traceback.format_exc())
                print('Error when program to get random message')

            is_success = True
            try:
                # find text input box
                logger.info('Trying to find input box')
                print('Trying to find input box')
                input_box = WebDriverWait(browser, 120).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
                )
                
                # input_box.send_keys(random_message)
                # paste_text(browser, input_box, random_message)
                for line in random_message.splitlines():
                    stoppage_line = random.randint(10, 20)
                    logger.info(f'Pause every {stoppage_line} character')
                    for idx, word in enumerate(line):
                        if ((idx+1) % stoppage_line) == 0:
                            time.sleep(random.randint(5, 10))
                        input_box.send_keys(word)
                        time.sleep(.3)
                    time.sleep(1)
                    input_box.send_keys(Keys.SHIFT, Keys.ENTER)

                logger.info(f'Trying to write message auto reply')
                print(f'Trying to write message auto reply')
            except TimeoutException:
                is_success = False
                logger.error('Timeout error to find input box.')
                logger.error(traceback.format_exc())
                print('Timeout error to find input box')
            except NoSuchElementException:
                is_success = False
                logger.error('Error no such element input box')
                logger.error(traceback.format_exc())
                print('Error no such element input box')

            if not is_success:
                failed_send_autoreply = f'Failed to send auto reply message to {phone}.'
                logger.error(failed_send_autoreply)
                print(failed_send_autoreply)
                data_report.extend([report_time_start, report_time_stop, phone, 'Error', failed_send_autoreply, ''])

                # write failed send auto reply message to excel
                fail_auto_reply_file = f'./report/reply_message/failed/send_auto_reply_message_{current_date}.xlsx'
                insert_excel(data_report, fail_auto_reply_file)
                logger.info('Successfully write failed send auto reply message to excel')
                print('Successfully write failed send auto reply message to excel')

                # write data auto reply message to txt file
                auto_reply_report = f'./report/reply_message/failed/send_auto_reply_message_{current_date}.txt'
                auto_reply_report_folder = Folder.is_exists(auto_reply_report)
                if not auto_reply_report_folder:
                    logger.info('Create folder for failed send auto reply message')
                    print('Create folder for failed send auto reply message')
                    Folder.mkdir(auto_reply_report)

                auto_reply_report = open(auto_reply_report, 'a')  # append mode
                auto_reply_report.write(f'{data_report[0]} | {time_start_autoreply} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {failed_send_autoreply} | \n')
                auto_reply_report.close()
                logger.info('Successfully write failed send auto reply message to txt file')
                print('Successfully write failed send auto reply message to txt file')

                data_report.clear()
                del time_start_autoreply, failed_send_autoreply, fail_auto_reply_file
                # skip current iteration
                continue

            time.sleep(5)
            # send message by press Enter
            logger.info('Trying to send auto reply message')
            print('Trying to send auto reply message')
            input_box.send_keys(Keys.ENTER)

            time_stop_autoreply = tools.get_datetime('%H:%M:%S')
            time.sleep(1)
            logger.info(f'Message auto_reply: {random_message}.')
            print(f'Message auto_reply: {random_message}.')

            try:
                success_send_autoreply = f'Successfully get data reply message from {phone}'
                data_report.extend([report_time_start, time_stop_autoreply, phone, 'Success', success_send_autoreply, random_message])

                # write success get data reply message to excel
                file_success = f'./report/reply_message/success/send_auto_reply_message_{current_date}.xlsx'
                insert_excel(data_report, file_success)
                logger.info('Successfully write success send auto reply message to excel')
                print('Successfully write success send auto reply message to excel')

                # write data auto reply message to txt file
                auto_reply_report = f'./report/reply_message/success/send_auto_reply_message_{current_date}.txt'
                auto_reply_report_folder = Folder.is_exists(auto_reply_report)
                if not auto_reply_report_folder:
                    logger.info('Create folder for success send auto reply message')
                    print('Create folder for success send auto reply message')
                    Folder.mkdir(auto_reply_report)

                auto_reply_report = open(auto_reply_report, 'a')  # append mode
                auto_reply_report.write(f'{data_report[0]} | {time_start_autoreply} | {time_stop_autoreply} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Success | {success_send_autoreply} | {random_message}\n')
                auto_reply_report.close()
                logger.info('Successfully write success send auto reply message to txt file')
                print('Successfully write success send auto reply message to txt file')
            except Exception as e:
                logger.error('Error when program to write success send auto reply message. Error: {e}'.format(e=e))
                logger.error(traceback.format_exc())
                print(e)
                continue

        time.sleep(random.randint(5, 8))

        # clear chat
        # clear_chat(browser)
        data_report.clear()

def get_data_reply_message(browser):
    list_message = list()
    logger.info('Trying to get data reply message')
    print('\nTrying to get data reply message')
    chat_list = browser.find_elements(By.CSS_SELECTOR, 'div#main div.copyable-area div.message-in')
    print(chat_list)
    response = False
    for chat in chat_list:
        message_obj = dict()
        timestamp = None
        is_deleted = None
        text_message = None
        attach_file = None
        meta_file = None
        caption_file = None
        image = None
        sticker = None

        # get message reply info datetime or message reply time
        info_datetime = True
        try:
            logger.info('Trying to get message reply datetime text chat info')
            print('\n\nTrying to get message reply datetime text chat info')
            selector = 'div#main div.copyable-area div.message-in div > .copyable-text'
            timestamp_message = chat.find_element(By.CSS_SELECTOR, selector).get_attribute('data-pre-plain-text')
            print(f'timestamp_message: {timestamp_message}')
            if timestamp_message:
                timestamp = reformat_chat_datetime(timestamp_message.strip(), '[]')
            else:
                info_datetime = False
        except NoSuchElementException as e:
            info_datetime = False
            logger.error('Datetime info is not found in message reply')
            print('Datetime info is not found in message reply')

        if not info_datetime:
            try:
                logger.info('Trying to get message reply time text chat')
                print('Trying to get message reply time text chat')
                time_selector = 'div.message-in div > div.xx3o462 > span[dir="auto"]'
                times = chat.find_element(By.CSS_SELECTOR, time_selector).text.strip()
                timestamp = times
            except NoSuchElementException as e:
                logger.error('Time info is not found in message reply')
                print('Time info is not found in message reply')

        # get delete message
        try:
            logger.info('Trying to get delete message info')
            print('Trying to get delete message info')
            icon_deleted = 'div.message-in.focusable-list-item span[data-icon="recalled"]'
            delete_msg = chat.find_element(By.CSS_SELECTOR, icon_deleted)
            if delete_msg:
                is_deleted = 'This message was deleted'

            # info_deleted = 'div.message-in.focusable-list-item > div > div > div > div > div:nth-child(2)'
            # is_deleted = chat.find_element(By.CSS_SELECTOR, info_deleted).text.strip()
        except NoSuchElementException as e:
            logger.error('Delete info message is not found in message reply')
            print('Delete info message is not found in message reply')

        time.sleep(1)
        # get info text message reply
        try:
            text_message = chat.find_element(By.CSS_SELECTOR, 'div.copyable-text span.copyable-text').text.strip()
        except NoSuchElementException as e:
            logger.error('Info text message reply is not found')
            time.sleep(0.005)

        # get info attach file
        try:
            file_selector = 'div.message-in.focusable-list-item > div > div > div > div > div > div > div:nth-child(2)'
            logger.info('Trying to get attach file info')
            print('Trying to get attach file info')
            attach_filename = f'{file_selector} > div > span[dir="auto"]'
            attach_file = chat.find_element(By.CSS_SELECTOR, attach_filename).text.strip()

            logger.info('Trying to get meta file info')
            print('Trying to get meta file info')
            meta_filename = f'{file_selector} > div:nth-child(2)'
            meta_file = chat.find_element(By.CSS_SELECTOR, meta_filename).text.strip()

            logger.info('Trying to get caption file info')
            print('Trying to get caption file info')
            caption_file = chat.find_element(By.CSS_SELECTOR, 'div.message-in .selectable-text.copyable-text').text.strip()
        except NoSuchElementException as e:
            logger.error('Attach file info is not found in message reply')
            time.sleep(0.005)

        # get info image
        try:
            logger.info('Trying to get image info')
            print('Trying to get image info')
            image_selector = 'div.message-in.focusable-list-item div[role="button"] > div > div:nth-child(2) img'
            image = chat.find_element(By.CSS_SELECTOR, image_selector).get_attribute('src').strip()
        except NoSuchElementException as e:
            logger.error('Image info is not found in message reply')
            time.sleep(0.005)

        # get info sticker
        try:
            logger.info('Trying to get sticker info')
            print('Trying to get sticker info')
            sticker_selector = 'div.message-in.focusable-list-item div > span > img[alt*="Sticker"]'
            sticker = chat.find_element(By.CSS_SELECTOR, sticker_selector).get_attribute('src').strip()
        except NoSuchElementException as e:
            logger.error('Sticker is not found in message reply')
            time.sleep(0.005)

        message_obj['date_time'] = timestamp
        if is_deleted:
            message_obj['message'] = is_deleted

        if text_message:
            message_obj['message'] = text_message
            #if text_message.lower().strip().replace('\n', '') in ['yes', 'ya', 'setuju', 'ok', 'boleh']:
            if message_obj['message'] != '':
                response = True
                logger.info('Message match with response format. Will try to send reply.')
            else:
                logger.info('Message does not match response format. Will not send reply.')

        if attach_file:
            message_obj['filename'] = attach_file

        if meta_file:
            message_obj['file_info'] = meta_file

        if image:
            message_obj['image'] = image

        if caption_file:
            message_obj['caption'] = caption_file

        if sticker:
            message_obj['sticker'] = sticker

        list_message.append(message_obj)

    return list_message, response

def scroll_chat(browser):
    print('Start scroll chat')
    time.sleep(2)
    chat = browser.find_element(By.CSS_SELECTOR, Selectors.CONVERSATION_PANEL)
    time.sleep(2)

    scroll_origin = ScrollOrigin.from_element(chat, 0, -50)
    for i in range(5):
        ActionChains(browser)\
            .scroll_from_origin(scroll_origin, 0, -5000 * i)\
            .perform()

    logger.info('Successfully scroll page')
    print('Successfully scroll page')

@csrf_exempt
def check_number_v2(request):
    if request.method == 'POST':
        data = request.POST
        files = request.FILES

        file = files.get('file')
        if not file:
            logger.warning('File phone list is empty')
            print('File phone list is empty')

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'File phone list is required'
                }), headers=headers, status=400
            )

        if not file.name.endswith('.txt'):
            logger.warning('Invalid file format. Only .txt files are allowed')
            print('Invalid file format. Only .txt files are allowed')

            del file

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'Invalid file format. Only .txt files are allowed'
                }), headers=headers, status=400
            )

        instance = data.get('instance', '')
        instance = instance.strip()
        if not instance:
            logger.warning('Instance browser is empty.')
            print('No instance found')

            del instance

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'Instance is required'
                }), headers=headers, status=400
            )

        # get driver browser from instance id
        browser = active_sessions.get(instance, None)
        if not browser:
            logger.error(f'No active instance browser {instance} found.')
            print('No active instance found')

            del browser

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': f'No active instance with instance id {instance} found'.format(instance=instance)
                }), headers=headers, status=400
            )

        # default start interval random value is 10800s (3h)
        start_interval = 10800
        start_value = data.get('start_interval', '')
        start_value = start_value.strip()
        if start_value:
            start_interval = int(start_value)

        # default end interval random value is 18000s (5h)
        end_interval = 18000
        end_value = data.get('end_interval', '')
        end_value = end_value.strip()
        if end_value:
            end_interval = int(end_value)

        # default total message of interval is 400
        total_number = 900
        message_count = data.get('total_number_interval', '')
        message_count = message_count.strip()
        if message_count:
            total_number = int(message_count)

        # default timeout is 300s
        timeout = 300
        timeout_interval = data.get('timeout', '')
        timeout_interval = timeout_interval.strip()
        if timeout_interval:
            timeout = int(timeout_interval)

        handles = len(browser.window_handles)
        if handles == 1:
            # open new tab
            Browser.new_tab(browser)

        # read phone number file
        files = files['file']

        logger.info(f"""start_interval: {start_interval}, end_interval: {end_interval},
                    total_limit_phone: {total_number} timeout: {timeout_interval}""")

        print('\nStart processing bulk check number whatsapp...')
        logger.info('Start processing bulk check number whatsapp.')

        # iterate the target number in array phone list
        for chunk in pd.read_csv(files, header=None, names=['phone'], chunksize=1):
            for index, row in chunk.iterrows():
                phone = row['phone']

                data_report = tools.get_datetime('%Y-%m-%d')
                time_start = time.perf_counter()
                print(f'\n{tools.get_datetime("%d-%m-%Y %H:%M:%S")}')
                print(f'{index + 1}. Processing check phone number {phone}')
                logger.info(f'{index + 1}. Processing check phone number {phone}')

                report_time_start = tools.get_datetime('%H:%M:%S')
                # check format phone number
                phone = str(phone)
                phone = phone.strip()
                phone_number = check_format_number(phone)
                # skip if result from check_format_number is empty
                if not phone_number:
                    report_time_stop = tools.get_datetime('%H:%M:%S')
                    invalid_no_message = f'Incorrect format mobile phone number: {phone}'
                    print(f'----| {invalid_no_message}')
                    logger.error(f'{invalid_no_message}')

                    # write invalid phone number report to txt file
                    file_invalid_number = f'./report/check_number/invalid/invalid_number_{current_date}.txt'
                    report_file_folder = Folder.is_exists(file_invalid_number)
                    if not report_file_folder:
                        logger.info('Create folder for invalid phone number')
                        print('Create folder for invalid phone number')
                        Folder.mkdir(file_invalid_number)

                    report_file = open(file_invalid_number, 'a')  # append mode
                    report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {invalid_no_message}\n')
                    report_file.close()
                    logger.info('Successfully write invalid phone number to txt file')
                    print('Successfully write invalid phone number to txt file')

                    # write invalid phone number to txt file
                    blast_invalid_number = f'./report/check_number/invalid/blast_invalid_number_{current_date}.txt'
                    report_file_folder = Folder.is_exists(blast_invalid_number)
                    if not report_file_folder:
                        logger.info('Create folder for blast invalid phone number')
                        print('Create folder for blast invalid phone number')
                        Folder.mkdir(blast_invalid_number)

                    report_file = open(blast_invalid_number, 'a')  # append mode
                    report_file.write(f'{phone}\n')
                    report_file.close()
                    logger.info('Successfully write blast invalid phone number to txt file')
                    print('Successfully write blast invalid phone number to txt file')

                    del report_time_start, report_time_stop, invalid_no_message, file_invalid_number, phone_number, phone, report_file
                    del file_invalid_number, blast_invalid_number, report_file_folder
                    # skip current iteration
                    continue

                # open chat URL to this number and wait for window/chats to load
                browser.get(CHAT_URL.format(phone=phone_number))
                logger.info(f'Open chat URL to check phone number {phone_number}.')
                print(f'Open chat URL to check phone number {phone_number}.')

                # wait until page is loaded
                is_timeout = False
                try:
                    logger.info('Waiting for page to load to check phone number')
                    print('Waiting for page to load to check phone number')
                    WebDriverWait(browser, timeout).until(lambda driver: (
                        element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
                    ))
                except Exception as e:
                    is_timeout = True
                    report_time_stop = tools.get_datetime('%H:%M:%S')
                    timeout_msg = f'Timeout error waiting for page to load to check phone number {phone_number}.'
                    print(f'----| {timeout_msg}')
                    logger.error(f'{timeout_msg}. Error: {e}')

                if is_timeout:
                    # write timeout phone number report to txt file
                    file_timeout_number = f'./report/check_number/timeout/timeout_check_{current_date}.txt'
                    report_file_folder = Folder.is_exists(file_timeout_number)
                    if not report_file_folder:
                        logger.info('Create folder for timeout phone number')
                        print('Create folder for timeout phone number')
                        Folder.mkdir(file_timeout_number)

                    report_file = open(file_timeout_number, 'a')  # append mode
                    report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {timeout_msg}\n')
                    report_file.close()
                    logger.info('Successfully write timeout phone number to txt file')
                    print('Successfully write timeout phone number to txt file')

                    # write timeout phone number to txt file
                    blast_timeout_number = f'./report/check_number/timeout/blast_timeout_check_{current_date}.txt'
                    report_file_folder = Folder.is_exists(blast_timeout_number)
                    if not report_file_folder:
                        logger.info('Create folder for blast timeout phone number')
                        print('Create folder for blast timeout phone number')
                        Folder.mkdir(blast_timeout_number)

                    report_file = open(blast_timeout_number, 'a')  # append mode
                    report_file.write(f'{phone}\n')
                    report_file.close()
                    logger.info('Successfully write blast timeout phone number to txt file')
                    print('Successfully write blast timeout phone number to txt file')

                    del time_start, file_timeout_number, is_timeout, report_time_start, report_time_stop, timeout_msg, phone_number, phone, report_file
                    del blast_timeout_number, report_file_folder
                    # skip current iteration when timeout
                    continue

                time.sleep(random.randint(10, 15))

                # verify the existence of a phone number on Whatsapp
                number_exists = True
                try:
                    logger.info('Trying to find phone number on conversation panel WhatsApp Web')
                    print('Trying to find phone number on WhatsApp Web')
                    browser.find_element(By.CSS_SELECTOR, Selectors.CONVERSATION_PANEL)
                except NoSuchElementException:
                    number_exists = False

                if not number_exists:
                    report_time_stop = tools.get_datetime('%H:%M:%S')
                    not_exist_msg = f'Phone number {phone_number} is not exist on whatsapp or invalid'
                    print(f'----| {not_exist_msg}')
                    logger.error(f'{not_exist_msg}.')

                    # write invalid phone number report to txt file
                    file_invalid_number = f'./report/check_number/invalid/invalid_number_{current_date}.txt'
                    report_file_folder = Folder.is_exists(file_invalid_number)
                    if not report_file_folder:
                        logger.info('Create folder for invalid phone number')
                        print('Create folder for invalid phone number')
                        Folder.mkdir(file_invalid_number)

                    report_file = open(file_invalid_number, 'a')  # append mode
                    report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {not_exist_msg}\n')
                    report_file.close()
                    logger.info('Successfully write invalid phone number to txt file')
                    print('Successfully write invalid phone number to txt file')

                    # write invalid phone number to txt file
                    blast_invalid_number = f'./report/check_number/invalid/blast_invalid_number_{current_date}.txt'
                    report_file_folder = Folder.is_exists(blast_invalid_number)
                    if not report_file_folder:
                        logger.info('Create folder for blast invalid phone number')
                        print('Create folder for blast invalid phone number')
                        Folder.mkdir(blast_invalid_number)

                    report_file = open(blast_invalid_number, 'a')  # append mode
                    report_file.write(f'{phone}\n')
                    report_file.close()
                    logger.info('Successfully write blast invalid phone number to txt file')
                    print('Successfully write blast invalid phone number to txt file')

                    del file_invalid_number, not_exist_msg, report_file, blast_invalid_number, report_file_folder

                    # close pop up information phone number is invalid
                    # try:
                    #     popup = WebDriverWait(browser, timeout).until(
                    #         EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.POPUP_CONFIRM))
                    #     )
                    #     time.sleep(3)
                    #     popup.click()
                    # except NoSuchElementException:
                    #     logger.debug(f'Unable to close pop up error invalid phone number {phone_number} on whatsapp')

                else:
                    report_time_stop = tools.get_datetime('%H:%M:%S')
                    valid_no_msg = f'Phone number {phone_number} is valid'
                    print(valid_no_msg)
                    logger.info(valid_no_msg)

                    # write valid phone number report to txt file
                    file_valid_number = f'./report/check_number/valid/valid_number_{current_date}.txt'
                    report_file_folder = Folder.is_exists(file_valid_number)
                    if not report_file_folder:
                        logger.info('Create folder for valid phone number')
                        print('Create folder for valid phone number')
                        Folder.mkdir(file_valid_number)

                    report_file = open(file_valid_number, 'a')  # append mode
                    report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Success | {valid_no_msg}\n')
                    report_file.close()
                    logger.info('Successfully write valid phone number to txt file')
                    print('Successfully write valid phone number to txt file')

                    # write valid phone number to txt file
                    blast_valid_number = f'./report/check_number/valid/blast_valid_number_{current_date}.txt'
                    report_file_folder = Folder.is_exists(blast_valid_number)
                    if not report_file_folder:
                        logger.info('Create folder for blast valid phone number')
                        print('Create folder for blast valid phone number')
                        Folder.mkdir(blast_valid_number)

                    report_file = open(blast_valid_number, 'a')  # append mode
                    report_file.write(f'{phone}\n')
                    report_file.close()
                    logger.info('Successfully write blast valid phone number to txt file')
                    print('Successfully write blast valid phone number to txt file')

                    del file_valid_number, valid_no_msg, report_file, blast_valid_number, report_file_folder

                del is_timeout, number_exists, report_time_start, report_time_stop
                time.sleep(1)

                # close conversation panel
                logger.info('Trying to close conversation panel')
                print('Trying to close conversation panel')
                browser.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)

                # set interval time after reaching of total phone numbers
                if index % total_number == 0 and index > 0:
                    interval = random.randint(start_interval, end_interval)
                    print(f'----| Wait for {interval}s to check the next number')
                    items = list(range(interval, 0, -1))
                    del interval

                    print('\n\n')
                    for _ in countdown(items, prefix = 'Next check number in:'):
                        time.sleep(1)

                    del items

                else:
                    random_number = random.randint(3, 6)
                    print(f'----| Rest in {random_number}s')
                    time.sleep(random_number)
                    del random_number

                # measure mobile number checkting time
                time_end = time.perf_counter() - time_start
                print(f'----| It takes {time_end:.2f}s to check phone number')

                del time_start, time_end

        if handles > 1:
            Browser.close_tab(browser)

        # Upload report to server
        thread = Thread(target=sync_report)
        thread.start()
        thread.join()  # Wait for the thread to finish

        del data, files, instance, browser, phone, index, start_interval, start_value, end_interval, end_value
        del total_number, message_count, timeout, timeout_interval, handles
        logger.info(f'Successfully check phone number list')
        print('\nSuccessfully check phone number list\n')
        return HttpResponse(
            json.dumps({
                'status': 'success',
                'message': 'Successfully check phone number list'
            }),
            headers=headers,
            status=200
        )

    else:
        return HttpResponse(status=405)

@csrf_exempt
def bulk_send_v2(request):
    if request.method == 'POST':
        data = request.POST
        files = request.FILES

        required_files = ['phone_list_file', 'dialogue_file', 'soceng_file', 'message_file', 'opening_decorator', 'opening_message', 'closing_message', 'closing_decorator']
        optional_files = ['auto_reply_file']

        # Check if required files are present and have valid format
        for file_name in required_files:
            file = files.get(file_name)
            if not file:
                logger.warning(f'{file_name} is empty')
                print(f'{file_name} is empty')

                del file

                return HttpResponse(
                    json.dumps({
                        'status': 'error',
                        'message': f'{file_name} is required'
                    }), headers=headers, status=400
                )

            if not file.name.endswith('.txt'):
                logger.warning('Invalid file format. Only .txt files are allowed')
                print('Invalid file format. Only .txt files are allowed')

                del file

                return HttpResponse(
                    json.dumps({
                        'status': 'error',
                        'message': 'Invalid file format. Only .txt files are allowed'
                    }), headers=headers, status=400
                )

        # Check optional files for valid format
        for file_name in optional_files:
            file = files.get(file_name)
            if file:
                if not file.name.endswith('.txt'):
                    logger.warning(f'Invalid file format for {file_name}. Only .txt files are allowed')
                    print(f'Invalid file format for {file_name}. Only .txt files are allowed')

                    del file

                    return HttpResponse(
                        json.dumps({
                            'status': 'error',
                            'message': f'Invalid file format for {file_name}. Only .txt files are allowed'
                        }), headers=headers, status=400
                    )

        phone_list_file = files['phone_list_file']
        soceng_file = files['soceng_file']
        dialogue_file = files['dialogue_file']
        message_file = files['message_file']
        auto_reply_file = files['auto_reply_file']
        opening_decorator_file = files['opening_decorator']
        opening_message_file = files['opening_message']
        closing_message_file = files['closing_message']
        closing_decorator_file = files['closing_decorator']

        # Check if file is present and has valid content
        if opening_decorator_file.size == 0:
            logger.warning('Opening decorator file is empty')
            print('Opening decorator file is empty')
            opening_decorator_file = None

        if opening_message_file.size == 0:
            logger.warning('Opening message file is empty')
            print('Opening message file is empty')
            opening_message_file = None

        if closing_decorator_file.size == 0:
            logger.warning('Closing decorator file is empty')
            print('Closing decorator file is empty')
            closing_decorator_file = None

        if closing_message_file.size == 0:
            logger.warning('Closing message file is empty')
            print('Closing message file is empty')
            closing_message_file = None

        if soceng_file.size == 0:
            logger.warning('Soceng file is empty')
            print('Soceng file is empty')
            soceng_file = None

        if dialogue_file.size == 0:
            logger.warning('Dialogue file is empty')
            print('Dialogue file is empty')
            dialogue_file = None

        instance = data.get('instance', '')
        instance = instance.strip()
        if not instance:
            logger.warning('Instance browser is empty.')
            print('No instance found')

            del instance

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'Instance is required'
                }), headers=headers, status=400
            )

        # get driver browser from instance id
        browser = active_sessions.get(instance, None)
        if not browser:
            logger.error(f'No active instance browser {instance} found.')
            print('No active instance found')

            del browser

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': f'No active instance with instance id {instance} found'.format(instance=instance)
                }), headers=headers, status=400
            )

        # default start interval random value is 10800s (3h)
        start_interval = int(os.getenv('START_INTERVAL', '10800'))
        start_value = data.get('start_interval', '')
        start_value = start_value.strip()
        if start_value:
            start_interval = int(start_value)

        # default end interval random value is 18000s (5h)
        end_interval = int(os.getenv('END_INTERVAL', '18000'))
        end_value = data.get('end_interval', '')
        end_value = end_value.strip()
        if end_value:
            end_interval = int(end_value)

        # default random value for start interval dialogue is 300s (5m)
        dialogue_start_interval = int(os.getenv('DEFAULT_DIALOGUE_START_INTERVAL', '300'))
        dialogue_start = data.get('dialogue_start_interval', '')
        dialogue_start = dialogue_start.strip()
        if dialogue_start:
            dialogue_start_interval = int(dialogue_start)

        # default random value for end interval dialogue is 900s (15m)
        dialogue_end_interval = int(os.getenv('DEFAULT_DIALOGUE_END_INTERVAL', '900'))
        dialogue_end = data.get('dialogue_end_interval', '')
        dialogue_end = dialogue_end.strip()
        if dialogue_end:
            dialogue_end_interval = int(dialogue_end)

        # default random value for start interval soceng is 6s
        soceng_start_interval = int(os.getenv('DEFAULT_SOCENG_START_INTERVAL', '6'))
        soceng_start = data.get('soceng_start_interval', '')
        soceng_start = soceng_start.strip()
        if soceng_start:
            soceng_start_interval = int(soceng_start)

        # default random value for end interval dialogue is 12s
        soceng_end_interval = int(os.getenv('DEFAULT_SOCENG_END_INTERVAL', '12'))
        soceng_end = data.get('soceng_end_interval', '')
        soceng_end = soceng_end.strip()
        if soceng_end:
            soceng_end_interval = int(soceng_end)

        # default total message of interval is 400
        total_message = int(os.getenv('DEFAULT_TOTAL_MESSAGE', '400'))
        message_count = data.get('total_message_interval', '')
        message_count = message_count.strip()
        if message_count:
            total_message = int(message_count)

        # default timeout is 300s
        timeout = int(os.getenv('DEFAULT_TIMEOUT', '300'))
        timeout_interval = data.get('timeout', '')
        timeout_interval = timeout_interval.strip()
        if timeout_interval:
            timeout = int(timeout_interval)

        browser.switch_to.window(browser.window_handles[0])
        handles = browser.window_handles
        for _, handle in enumerate(handles):
            if handle != browser.current_window_handle:
                browser.switch_to.window(handle)
                browser.close()

        browser.switch_to.window(browser.window_handles[0])
        event = Event()

        message_index = 0
        opening_decorator_idx = 0
        opening_msg_idx = 0
        closing_decorator_idx = 0
        closing_msg_idx = 0

        # limit message wa
        message_limit = 0
        total_message_limit_first = int(os.getenv('TOTAL_BLAST_MIN', '900'))
        total_message_limit_last = int(os.getenv('TOTAL_BLAST_MAX', '999'))
        random_message_limit = random.randint(total_message_limit_first, total_message_limit_last)

        msg_limit_file = open(f'log/tmp_message_limit.txt', 'w')
        msg_limit_file.write(str(0))
        msg_limit_file.close

        # read phone number file
        files = pd.read_csv(phone_list_file, header=None, names=['phone'], chunksize=1)

        logger.info(f"""start_interval: {start_interval}, end_interval: {end_interval},
                    dialogue_start_interval: {dialogue_start_interval}, dialogue_end_interval: {dialogue_end_interval},
                    total_message: {total_message}, timeout: {timeout_interval}""")

        is_auto_reply = data.get('is_auto_reply', '')
        is_auto_reply = is_auto_reply.strip().lower()
        if is_auto_reply == 'true':
            is_auto_reply = True
        else:
            is_auto_reply = False

        # Check if auto_reply_file size is empty
        if auto_reply_file.size == 0:
            logger.warning('Auto reply file is empty')
            auto_reply_file = None

        # Check reply message before start blast
        auto_reply_message(browser, auto_reply_file, auto_reply_conf=is_auto_reply, type_log_msg='before start blast')

        df_message = pd.read_csv(message_file, header=None)
        df_opening_decorator = pd.read_csv(opening_decorator_file, header=None) if opening_decorator_file else None
        df_opening_message = pd.read_csv(opening_message_file, header=None) if opening_message_file else None
        df_closing_message = pd.read_csv(closing_message_file, header=None) if closing_message_file else None
        df_closing_decorator = pd.read_csv(closing_decorator_file, header=None) if closing_decorator_file else None

        total_row_opening_decorator = len(df_opening_decorator) if df_opening_decorator is not None else 0
        total_row_opening_message = len(df_opening_message) if df_opening_message is not None else 0
        total_row_closing_message = len(df_closing_message) if df_closing_message is not None else 0
        total_row_closing_decorator = len(df_closing_decorator) if df_closing_decorator is not None else 0

        check_reply_interval_min = data.get('auto_reply_check_interval', '')
        check_reply_interval_max = data.get('auto_reply_check_interval_max', '')
        check_reply_interval_min = check_reply_interval_min.strip()
        check_reply_interval_max = check_reply_interval_max.strip()
        # add a counter to check reply message
        message_counter = 0
        # if check_reply_interval is not empty, convert to integer
        if check_reply_interval_min:
            check_reply_interval_min = int(check_reply_interval_min)
        if check_reply_interval_min:
            check_reply_interval_max = int(check_reply_interval_max)

        check_reply_interval = random.randint(check_reply_interval_min, check_reply_interval_max)
        
        # timeout counter for blast message
        timeout_counter = 0

        print('\nStart processing bulk send whatsapp...')
        logger.info('Start processing bulk send whatsapp.')
        # iterate the target number in array phone list
        for chunk in files:
            for index, row in chunk.iterrows():
                phone = row['phone']
                data_report = tools.get_datetime('%Y-%m-%d')
                time_start = time.perf_counter()

                msg_limit_file = open(f'log/tmp_message_limit.txt', 'r')
                tmp_msg_limit = msg_limit_file.read()
                msg_limit_file.close

                # set default tmp_msg_limit to message_limit if msg_limit_file is empty
                if not tmp_msg_limit:
                    tmp_msg_limit = message_limit

                message_limit = int(tmp_msg_limit)

                # stop blast message when process send message reach random_message_limit
                if message_limit == random_message_limit or message_limit > random_message_limit:
                    print(f'----| Total message limit is reached')
                    logger.info(f'Total message limit is reached')

                    del data_report, time_start, msg_limit_file, tmp_msg_limit, message_limit
                    break

                print(f'\n{tools.get_datetime("%d-%m-%Y %H:%M:%S")}')
                print(f'{index + 1}. Trying to send message to {phone}')
                logger.info(f'{index + 1}. Trying to send message to {phone}')

                report_time_start = tools.get_datetime('%H:%M:%S')
                # check format phone number
                phone = str(phone)
                phone = phone.strip()
                phone_number = check_format_number(phone)
                report_time_stop = tools.get_datetime('%H:%M:%S')
                # skip iteration if result from check_format_number is empty
                if not phone_number:
                    invalid_no_message = f'Incorrect format mobile phone number: {phone}'
                    print(invalid_no_message)
                    logger.error(invalid_no_message)

                    # write failed send message phone number to txt file
                    failed_number = f'./report/send/failed/failed_send_{current_date}.txt'
                    report_file_folder = Folder.is_exists(failed_number)
                    if not report_file_folder:
                        logger.info('Create folder for failed send message')
                        print('Create folder for failed send message')
                        Folder.mkdir(failed_number)

                    report_file = open(failed_number, 'a')  # append mode
                    report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {invalid_no_message}\n')
                    logger.info('Successfully write failed send message to txt file')
                    print('Successfully write failed send message to txt file')

                    del time_start, failed_number, invalid_no_message, failed_number, report_time_start, report_time_stop, phone_number, phone
                    del data_report, time_start, msg_limit_file, tmp_msg_limit, message_limit
                    # skip current iteration
                    continue

                if event.is_set():
                    logger.info('Event is set. Stop the process blast message')
                    print('Event is set. Stop the process blast message')
                    Browser.close_tab(browser)

                handles = len(browser.window_handles)
                if handles == 1:
                    # open new tab
                    Browser.new_tab(browser)

                # open chat URL to this number and wait for window/chats to load
                logger.info(f'Open chat URL to send message to {phone_number}.')
                print(f'Open chat URL to send message to {phone_number}.')
                browser.get(CHAT_URL.format(phone=phone_number))
                time.sleep(6)

                # check if the page is loaded
                try:
                    logger.info('Waiting for page to load chat')
                    print('Waiting for page to load chat')
                    WebDriverWait(browser, timeout).until(lambda driver: (
                        element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
                    ))
                except TimeoutException:
                    # if timeout greater than 5 than stop the process blast message
                    timeout_counter += 1
                    if timeout_counter > 5:
                        logger.info('Stopping the process blast. Timeout is greater than 5.')
                        print('Stopping the process blast. Timeout is greater than 5.')

                        # upload report to server
                        thread = Thread(target=sync_report)
                        thread.start()
                        thread.join()  # Wait for the thread to finish
                        break

                    report_time_stop = tools.get_datetime('%H:%M:%S')
                    timeout_msg = f'Timeout error waiting for page to load chat from {phone_number}.'
                    logger.error(timeout_msg)
                    print(f'----| {timeout_msg}')

                    # write timeout phone number to txt file
                    file_timeout_number = f'./report/send/timeout/timeout_send_{current_date}.txt'
                    report_file_folder = Folder.is_exists(file_timeout_number)
                    if not report_file_folder:
                        logger.info('Create folder for timeout phone number')
                        print('Create folder for timeout phone number')
                        Folder.mkdir(file_timeout_number)

                    report_file = open(file_timeout_number, 'a')  # append mode
                    report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {timeout_msg} | {message}\n')
                    report_file.close()
                    logger.info('Successfully write timeout phone number to txt file')
                    print('Successfully write timeout phone number to txt file')

                    del file_timeout_number, report_time_start, report_time_stop, timeout_msg, phone_number, phone
                    del data_report, time_start, msg_limit_file, tmp_msg_limit, message_limit
                    del handles
                    # skip current iteration when timeout
                    continue

                time.sleep(3)

                # dynamic blast message
                # get next message
                if index + 1 > 1 and total_message > 0:
                    message_index = message_index + 1
                    opening_decorator_idx = opening_decorator_idx + 1
                    opening_msg_idx = opening_msg_idx + 1
                    closing_msg_idx = closing_msg_idx + 1
                    closing_decorator_idx = closing_decorator_idx + 1

                # reset message to beginning
                if message_index >= df_message.shape[0]:
                    message_index = 0

                if opening_decorator_idx >= total_row_opening_decorator:
                    opening_decorator_idx = 0

                if opening_msg_idx >= total_row_opening_message:
                    opening_msg_idx = 0

                if closing_msg_idx >= total_row_closing_message:
                    closing_msg_idx = 0

                if closing_decorator_idx >= total_row_closing_decorator:
                    closing_decorator_idx = 0

                message = df_message[0][message_index]
                opening_decorator = df_opening_decorator[0][opening_decorator_idx] if opening_decorator_file is not None else ''
                opening_message = df_opening_message[0][opening_msg_idx] if opening_message_file is not None else ''
                closing_message = df_closing_message[0][closing_msg_idx] if closing_message_file is not None else ''
                closing_decorator = df_closing_decorator[0][closing_decorator_idx] if closing_decorator_file is not None else ''

                # Remove empty string from the list
                list_message = [opening_decorator, opening_message, message, closing_message, closing_decorator]
                messages = [msg_item for msg_item in list_message if msg_item != '']
                # Join the variables with a new line
                combined_message = '\n\n'.join(messages)

                is_success = True
                try:
                    # find text input box
                    logger.info('Trying to find text input box')
                    print('Trying to find text input box')
                    input_box = WebDriverWait(browser, 120).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
                    )
                    logger.info(f'Message blast: \n{combined_message}')
                    print(f'Message blast: \n{combined_message}')
                    paste_text(browser, input_box, combined_message)

                    time.sleep(10)

                    # send message by press Enter
                    input_box.send_keys(Keys.ENTER)
                    report_time_stop = tools.get_datetime('%H:%M:%S')

                    del input_box

                    time.sleep(random.randint(4, 7))
                except Exception as e:
                    is_success = False
                    failed_sending_msg = f'Failed send message to {phone_number}.'
                    logger.error(f'{failed_sending_msg}. Error: {e}')
                    print(f'----| {failed_sending_msg}')

                    # write failed send message phone number to txt file
                    failed_number = f'./report/send/failed/failed_send_{current_date}.txt'
                    report_file_folder = Folder.is_exists(failed_number)
                    if not report_file_folder:
                        logger.info('Create folder for failed send message')
                        print('Create folder for failed send message')
                        Folder.mkdir(failed_number)

                    report_file = open(failed_number, 'a')  # append mode
                    report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {failed_sending_msg} | {combined_message}\n')
                    report_file.close()
                    logger.info('Successfully write failed send message to txt file')
                    print('Successfully write failed send message to txt file')

                    del failed_number, failed_sending_msg, report_time_start, report_time_stop, phone_number, phone
                    del handles, data_report, time_start, msg_limit_file, tmp_msg_limit, message_limit
                    # skip current iteration
                    continue

                if is_success:
                    success_sending_msg = f'Successfully sending message to {phone_number}'
                    print(f'----| {success_sending_msg}')
                    logger.info(success_sending_msg)

                    # write timeout phone number to txt file
                    success_number = f'./report/send/success/success_send_{current_date}.txt'
                    report_file_folder = Folder.is_exists(success_number)
                    if not report_file_folder:
                        logger.info('Create folder for success send message')
                        print('Create folder for success send message')
                        Folder.mkdir(success_number)

                    report_file = open(success_number, 'a')  # append mode
                    report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Success | {success_sending_msg} | {combined_message}\n')
                    report_file.close()
                    logger.info('Successfully write success send message to txt file')
                    print('----| Successfully write success send message to txt file')

                    message_limit = message_limit + 1
                    msg_limit_file = open(f'log/tmp_message_limit.txt', 'w')
                    msg_limit_file.write(str(message_limit))
                    msg_limit_file.close
                    del success_number

                    msg_limit_file = open(f'log/tmp_message_limit.txt', 'r')
                    tmp_msg_limit = msg_limit_file.read()
                    msg_limit_file.close
                    del msg_limit_file, tmp_msg_limit, handles, data_report, report_time_start, report_time_stop, phone

                # measure sending message time
                time_end = time.perf_counter() - time_start
                print(f'----| It takes {time_end:.2f}s for sending message to {phone_number}')
                del time_start, time_end, phone_number, message, combined_message

                # close tab
                Browser.close_tab(browser)

                # if success sending message, start checking reply message in interval message
                if is_success:
                    message_counter += 1
                    if check_reply_interval and message_counter % check_reply_interval == 0:
                        # start checking reply message in interval message
                        auto_reply_message(browser, auto_reply_file, auto_reply_conf=is_auto_reply, type_log_msg='in interval message')

                # set interval time after reaching of total messages
                if index % total_message == 0 and index > 0:
                    # delete the group chat before the social engineering process program begins
                    # logger.info('Delete group chat before the dialogue process program begins')
                    # print('----| Delete group chat before the dialogue process program begins')
                    # threads_group_chat = Thread(target=clear_all_group_chat, args=(browser,))
                    # logger.info('Start thread clear group chat')
                    # threads_group_chat.start()
                    # wait for thread clear group chat to finish
                    # logger.info('Wait for thread clear group chat to finish')
                    # threads_group_chat.join()
                    # del threads_group_chat

                    interval = random.randint(start_interval, end_interval)
                    print(f'----| Wait for {interval}s to send the next message')
                    items = list(range(interval, 0, -1))
                    del interval

                    dialogue_file.file.seek(0)
                    logger.info('Start dialogue chat')
                    print('----| Start dialogue chat')
                    threads = Thread(target=dialogue_v2, args=(browser, dialogue_file, dialogue_start_interval, dialogue_end_interval, timeout, event, message_limit, random_message_limit, 'dialogue'))
                    logger.info('Start thread dialogue chat')
                    threads.start()

                    print('\n\n')
                    for _ in countdown(items, prefix = 'Next blast message in:'):
                        time.sleep(1)

                    del items

                    # stop dialogue chat when no interval blast message
                    logger.info('Stop dialogue chat when no interval blast message')
                    event.set()
                    # wait for new thread to finish
                    logger.info('Wait for thread dialogue chat to finish')
                    threads.join()
                    # reset event to false
                    logger.info('Reset event to false')
                    event.clear()

                else:
                    soceng_file.file.seek(0)
                    logger.info('Start social engineering')
                    print('\n----| Start social engineering')
                    threads = Thread(target=dialogue_v2, args=(browser, soceng_file, soceng_start_interval, soceng_end_interval, timeout, event, message_limit, random_message_limit, 'soceng'))
                    logger.info('Start thread social engineering')
                    threads.start()

                    # random_number = random.randint(5, 8)
                    # print(f'----| Rest in {random_number}s')
                    # time.sleep(random_number)

                    # stop social engineering when program interval blast message is complete
                    # event.set() # change stop soceng process in soceng or dialogue
                    # wait for new thread to finish
                    logger.info('Wait for thread social engineering to finish')
                    threads.join()
                    # reset event to false
                    logger.info('Reset event to false')
                    event.clear()
                    # del random_number

                del is_success, threads

        auto_reply_message(browser, auto_reply_file, auto_reply_conf=is_auto_reply, type_log_msg='after blast')

        # Upload report to server
        thread = Thread(target=sync_report)
        thread.start()
        thread.join()  # Wait for the thread to finish

        del data, files, instance, browser
        logger.info('Successfully sending bulk message')
        print('\nSuccessfully sending bulk message\n')
        return HttpResponse(
            json.dumps({
                'status': 'success',
                'message': 'Bulk message sent successfully'
            }),
            headers=headers,
            status=200
        )

    else:
        return HttpResponse(status=405)

def dialogue_v2(browser, file_path, start_interval, end_interval, timeout, event, message_limit, random_message_limit, chat_type = 'dialogue'):
    if not file_path:
        print(f'\nFile text for {chat_type} is not found')
        logger.info(f'File text for {chat_type} is not found.')
        del chat_type

        return None

    handles = len(browser.window_handles)
    if handles == 1:
        # open new tab
        Browser.new_tab(browser)

    # random 30 - 60 seconds
    random_sleep = random.randint(30, 60)
    logger.info(f'Wait in {random_sleep}s before start {chat_type}')
    print(f'----| Wait in {random_sleep}s before start {chat_type}')
    time.sleep(random_sleep)

    # read phone number file
    logger.info(f'Trying to read phone number file for {chat_type}')
    print(f'\nTrying to read phone number file for {chat_type}')
    # read the entire file
    dataframe = pd.read_csv(file_path, header=None, names=['phone', 'message'], delimiter='|')

    # Clear the file 'log/tmp_soceng_send.txt'
    tmp_soceng_send = 'log/tmp_soceng_send.txt'
    df_tmp_soceng_send = pd.read_csv(tmp_soceng_send, header=None, names=['phone', 'message'], delimiter='|')
    if (len(dataframe) - len(df_tmp_soceng_send)) <= 2:
        with open('log/tmp_soceng_send.txt', 'w') as file:
            file.write('')

    # load txt files tmp soceng message send
    tmp_soceng = pd.read_csv(tmp_soceng_send, header=None, names=['phone', 'message'], delimiter='|')
    # define the column to compare
    key_column = 'message'
    # find the rows in dataframe that are not in tmp_soceng
    new_df = dataframe[~dataframe[key_column].isin(tmp_soceng[key_column])]

    # Shuffle the DataFrame
    num_rows = random.randint(1, 3)
    random_df = new_df.sample(n=num_rows).reset_index(drop=True)

    # timeout counter for dialogue message
    timeout_counter = 0

    print(f'\n\n\nStart processing {num_rows} {chat_type}...')
    logger.info(f'Start processing {num_rows} {chat_type}')

    # iterate the target number in array phone list
    for index, row in random_df.iterrows():
        # check if the event is set
        if event.is_set():
            # if the event is set then stop soceng process
            break

        phone = row['phone']
        if pd.isna(phone):
            phone = ''

        message = row['message']
        if pd.isna(message):
            message = ''

        msg_limit_file = open(f'log/tmp_message_limit.txt', 'r')
        tmp_msg_limit = msg_limit_file.read()
        msg_limit_file.close

        # set default tmp_msg_limit to message_limit if msg_limit_file is empty
        if not tmp_msg_limit or int(tmp_msg_limit) == 0:
            tmp_msg_limit = message_limit

        msg_limit = int(tmp_msg_limit)

        # stop soceng when process total sending message reach random_message_limit
        if msg_limit == random_message_limit:
            print(f'----| Total message limit {chat_type} is reached')
            logger.info(f'Total message limit {chat_type} is reached')

            del msg_limit_file, tmp_msg_limit, msg_limit

            # stop soceng process
            event.set()
            # break

        # check if the event is set
        if event.is_set():
            logger.info(f'Event is set. Stop the process {chat_type}')

            # if the event is set then stop soceng process
            break

        time_start = time.perf_counter()
        print(f'\n{tools.get_datetime("%d-%m-%Y %H:%M:%S")}')
        print(f'{index + 1}. Trying to {chat_type} with number {phone}')
        logger.info(f'{index + 1}. Trying to {chat_type} with number {phone}')

        handles = len(browser.window_handles)
        if handles == 1:
            # open new tab
            Browser.new_tab(browser)

        data_report = tools.get_datetime('%Y-%m-%d')
        report_time_start = tools.get_datetime('%H:%M:%S')

        # check format phone number
        phone = str(phone)
        phone = phone.strip()
        phone_number = check_format_number(phone)
        # skip iteration if result from check_format_number is empty
        if not phone_number:
            report_time_stop = tools.get_datetime('%H:%M:%S')
            incorrect_no_msg = f'Incorrect format mobile phone number: {phone}.'
            print(incorrect_no_msg)
            logger.error(incorrect_no_msg)

            # write invalid phone number to txt file
            file_invalid_number = f'./report/{chat_type}/invalid/invalid_number_{chat_type}_{current_date}.txt'
            report_file_folder = Folder.is_exists(file_invalid_number)
            if not report_file_folder:
                logger.info('Create folder for invalid number report')
                print('----| Create folder for invalid number report')
                Folder.mkdir(file_invalid_number)

            report_file = open(file_invalid_number, 'a')  # append mode
            report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {incorrect_no_msg}\n')
            report_file.close()
            logger.info(f'Write invalid phone number to txt file')
            print(f'----| Write invalid phone number to txt file')

            del time_start, file_invalid_number, report_time_stop, incorrect_no_msg, phone_number, phone, handles, report_file
            # skip current iteration
            continue

        # open chat URL to this number and wait for window/chats to load
        logger.info(f'Open chat URL to this number {phone_number}.')
        print(f'----| Open chat URL to this number {phone_number}.')
        browser.get(CHAT_URL.format(phone=phone_number))
        time.sleep(7)
        logger.info(f'Waiting for page to load chat from {phone_number}.')

        try:
            logger.info(f'Trying to find search bar element to check conversation header')
            print(f'----| Trying to find search bar element to check conversation header')
            WebDriverWait(browser, 120).until(lambda driver: (
                element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
            ))
            time.sleep(2)
        except TimeoutException:
            report_time_stop = tools.get_datetime('%H:%M:%S')
            timeout_msg = f'Timeout error waiting for page to load chat.'
            print(timeout_msg)
            logger.error(timeout_msg)

            # write timeout phone number to txt file
            file_timeout_number = f'./report/{chat_type}/timeout/timeout_{chat_type}_{current_date}.txt'
            report_file_folder = Folder.is_exists(file_timeout_number)
            if not report_file_folder:
                logger.info('Create folder for timeout report')
                print('----| Create folder for timeout report')
                Folder.mkdir(file_timeout_number)

            report_file = open(file_timeout_number, 'a')  # append mode
            report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {timeout_msg} | {message}\n')
            report_file.close()
            logger.info(f'Write timeout phone number to txt file')
            print(f'----| Write timeout phone number to txt file')

            # if timeout greater than 5 than stop the process
            timeout_counter += 1
            if timeout_counter > 5:
                logger.info(f'Stopping the process {chat_type}. Timeout is greater than 5.')
                print(f'----| Stopping the process {chat_type}. Timeout is greater than 5.')

                # upload report to server
                thread = Thread(target=sync_report)
                thread.start()
                thread.join()  # Wait for the thread to finish
                break

            del report_time_stop, timeout_msg, file_timeout_number, phone, handles, report_file
            # skip current iteration when timeout
            continue
        except Exception as e:
            logger.error(f'Error when trying to check conversation header. Error: {e}')
            print('----| Error when trying to check conversation header')

        time.sleep(3)
        is_success = True
        # Check conversation header to identify phone number is valid
        try:
            lang_element = browser.find_element(By.CSS_SELECTOR, 'html').get_attribute('lang')
            logger.info(f'This WhatsApp web uses language: {lang_element}')
            conv_header = Selectors.CONVERSATION_HEADER_ID if lang_element == 'id' else Selectors.CONVERSATION_HEADER

            logger.info(f'Trying to check conversation header')
            print(f'----| Trying to check conversation header')
            browser.find_element(By.CSS_SELECTOR, conv_header)
        except NoSuchElementException as e:
            is_success = False
            logger.error(f'No such element conversation header, please check CSS Selector WhatsApp web. Error: {e}')
            print('----| No such element conversation header, please check CSS Selector WhatsApp web')

        except Exception as e:
            is_success = False
            logger.error(f'Error when trying to check conversation header. Error: {e}')
            print(f'----| Error when trying to check conversation header')

        if not is_success:
            try:
                WebDriverWait(browser, 120).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.POPUP))
                )
                # browser.find_element(By.CSS_SELECTOR, Selectors.POPUP_CONFIRM).click()
            except NoSuchElementException:
                is_success = True
                popup_not_found_msg = 'Error no such element popup invalid phone number, please check CSS Selector WhatsApp web.'
                print(popup_not_found_msg)
                logger.error(popup_not_found_msg)
                del popup_not_found_msg
            except TimeoutException:
                is_success = True
                timeout_dialoge_msg = f'Timeout when program trying to find popup invalid phone number.'
                print(timeout_dialoge_msg)
                logger.error(timeout_dialoge_msg)
                del timeout_dialoge_msg

            del is_success
            # skip current iteration when timeout
            continue
        else:
            logger.info(f'Message {chat_type}: {message}.')
            print(f'Message {chat_type}: \n{message}.\n')
            try:
                # find text input box
                logger.info(f'Trying to find text input box')
                print(f'----| Trying to find text input box')
                input_box = WebDriverWait(browser, 120).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
                )
                logger.info(f'Write message to text input box')
                print(f'----| Write message to text input box')
                for line in message.splitlines():
                    input_box.send_keys(line)
                    input_box.send_keys(Keys.SHIFT, Keys.ENTER)

                time.sleep(9)

                # send message by press Enter
                logger.info('Send message by press Enter')
                print(f'----| Send message by press Enter')
                input_box.send_keys(Keys.ENTER)
                report_time_stop = tools.get_datetime('%H:%M:%S')

                del input_box

                # write temp count message limit
                message_limit = message_limit + 1
                tmp_message_limit = open('log/tmp_message_limit.txt', 'w')
                tmp_message_limit.write(str(message_limit))
                tmp_message_limit.close
                del tmp_message_limit

                # write temp soceng send
                tmp_soceng_send_file = open('log/tmp_soceng_send.txt', 'a')
                tmp_soceng_send_file.write(f"{phone}|{message}\n")
                tmp_soceng_send_file.close
                del tmp_soceng_send_file

                time.sleep(5)
                # close tab
                Browser.close_tab(browser)
            except Exception as e:
                failed_sending_msg = f'Failed to {chat_type} with {phone_number}'
                print(failed_sending_msg)
                logger.error(failed_sending_msg + f' Error: {e}')
                report_time_stop = tools.get_datetime('%H:%M:%S')

                # write failed send message phone number to txt file
                failed_number = f'./report/{chat_type}/failed/failed_{chat_type}_{current_date}.txt'
                report_file_folder = Folder.is_exists(failed_number)
                if not report_file_folder:
                    logger.info(f'Create folder for failed report {chat_type}')
                    print(f'----| Create folder for failed report {chat_type}')
                    Folder.mkdir(failed_number)

                report_file = open(failed_number, 'a')  # append mode
                report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {failed_sending_msg} | {message}\n')
                report_file.close()
                logger.info(f'Write failed send message phone number to txt file')
                print(f'----| Write failed send message phone number to txt file')

                del failed_number, failed_sending_msg, report_time_start, report_time_stop, phone_number, phone, report_file
                # skip current iteration
                continue

        if is_success or not event.is_set():
            success_sending_msg = f'Successfully {chat_type} chat with {phone_number}'
            print(f'----| {success_sending_msg}')
            logger.info(success_sending_msg)

            # write success dialogue chat to txt file
            success_number = f'./report/{chat_type}/send/success_send_{current_date}.txt'
            report_file_folder = Folder.is_exists(success_number)
            if not report_file_folder:
                logger.info(f'Create folder for success report {chat_type}')
                print(f'----| Create folder for success report {chat_type}')
                Folder.mkdir(success_number)

            report_file = open(success_number, 'a')  # append mode
            report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Success | {success_sending_msg} | {message}\n')
            report_file.close()
            logger.info(f'Write success send message phone number to txt file')
            print(f'----| Write success send message phone number to txt file')
            del success_number, success_sending_msg, report_file

        # measure dialogue time
        time_end = time.perf_counter() - time_start
        print(f'----| It takes {time_end:.2f}s for {chat_type} with {phone_number}')
        del time_start, time_end, is_success, phone_number, phone, handles, data_report, report_time_start, report_time_stop, msg_limit

        random_number = random.randint(30, 60)
        print(f'\r----| Rest in {random_number}s\n')
        print('')
        time.sleep(random_number)
        del random_number

    print(f'\nProcessing {chat_type} is done\n')
    logger.info(f'Processing {chat_type} is done')

def auto_reply_message_v2(browser, input_data, dict_of_phone, auto_reply_conf, type_log_msg='in interval message'):

    if auto_reply_conf:
    
        print(f'\nStart checking reply message {type_log_msg}')
        logger.info(f'Start checking reply message {type_log_msg}')
        # Check reply message
        handles = len(browser.window_handles)
        if handles > 1:
            Browser.close_tab(browser)

        Browser.new_tab(browser)
        browser.get(BASE_URL)
        time.sleep(6)
        try:
            logger.info('Trying to make sure the search bar in home is available')
            print('Trying to make sure the search bar in home is available')
            WebDriverWait(browser, 90).until(lambda driver: (
                element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
            ))
            time.sleep(6)
          
            print(dict_of_phone)
            for key, value in dict_of_phone.items():
                data_report = [tools.get_datetime('%Y-%m-%d')]
                report_time_start = tools.get_datetime('%H:%M:%S')
                if value == 'unread':
                    # Trying to get Chat URL
                    try:
                        logger.info(f'Trying to get unread message from {key}')
                        logger.info(f'Tryping to open Chat box from {key}')
                        browser.get(CHAT_URL.format(phone=key))
                        time.sleep(10)
                        # scroll chat to top
                        # scroll_chat(browser)
                        # get reply message
                        data_reply, response = get_data_reply_message(browser)
                        print(f'After get data reply from {key}')
                        print(data_reply)
                        print(response)
                        success_get_reply = f'Successfully get data reply message from {key}'
                        report_time_stop = tools.get_datetime('%H:%M:%S')
                        data_report.extend([report_time_start, report_time_stop, key, 'Success', success_get_reply, data_reply])

                        # write success get data reply message to excel
                        file_success = f'./report/reply_message/reply_message_{current_date}.xlsx'
                        insert_excel(data_report, file_success)
                        logger.info('Successfully write success get reply message to excel')
                        print('Successfully write success get reply message to excel')

                        # write data reply message to txt file
                        file_reply_txt = f'./report/reply_message/reply_message_{current_date}.txt'
                        file_txt_folder = Folder.is_exists(file_reply_txt)
                        if not file_txt_folder:
                            logger.info('Create folder for reply message')
                            print('Create folder for reply message')
                            Folder.mkdir(file_reply_txt)

                        report_file_reply_txt = open(file_reply_txt, 'a')  # append mode
                        report_file_reply_txt.write(f'{data_report[0]} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {key} | Success | {success_get_reply} | {data_reply}\n')
                        report_file_reply_txt.close()
                        logger.info('Successfully write data reply message to txt file')
                        print('Successfully write data reply message to txt file')

                        logger.info(success_get_reply)
                        print(success_get_reply)

                        # Upload file report to server
                        thread = Thread(target=sync_report)
                        thread.start()
                        thread.join()  # Wait for the thread to finish

                        random_message = ['']
                        if auto_reply_conf and not input_data.empty and response:
                            try:
                                # delete array data in data_report except first data
                                data_report = data_report[:1]
                                time_start_autoreply = tools.get_datetime('%H:%M:%S')

                                print(f'Trying to send auto reply to {key}')
                                logger.info(f'Trying to send auto reply to {key}')
                                print('INI INPUT DATA SAAT SESUAI RESPON')
                                print(input_data)
                                logger.info('Trying to get random message')
                                data_message = input_data['message']
                                print('INI DATA MESSAGE')
                                print(data_message)
                                random_message = random.choice(data_message)
                                logger.info(f'Auto reply message: {random_message}')
                                print(f'Auto reply message: {random_message}')
                            except Exception as e:
                                logger.error('Error when program to get random message. Error: {e}'.format(e=e))
                                logger.error(traceback.format_exc())
                                print('Error when program to get random message')

                            is_success = True
                            try:
                                # find text input box
                                logger.info('Trying to find input box')
                                print('Trying to find input box')
                                input_box = WebDriverWait(browser, 120).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
                                )
                                # input_box.send_keys(random_message)
                                # paste_text(browser, input_box, random_message)
                                for line in random_message.splitlines():
                                    stoppage_line = random.randint(10, 20)
                                    logger.info(f'Pause every {stoppage_line} character')
                                    for idx, word in enumerate(line):
                                        if ((idx+1) % stoppage_line) == 0:
                                            time.sleep(random.randint(5, 10))
                                        input_box.send_keys(word)
                                        time.sleep(.3)
                                    #input_box.send_keys(line)
                                    time.sleep(1)
                                    input_box.send_keys(Keys.SHIFT, Keys.ENTER)

                                time.sleep(10)
                                logger.info(f'Trying to write message auto reply')
                                print(f'Trying to write message auto reply')
                            except TimeoutException:
                                is_success = False
                                logger.error('Timeout error to find input box.')
                                logger.error(traceback.format_exc())
                                print('Timeout error to find input box')
                            except NoSuchElementException:
                                is_success = False
                                logger.error('Error no such element input box')
                                logger.error(traceback.format_exc())
                                print('Error no such element input box')

                            if not is_success:
                                failed_send_autoreply = f'Failed to send auto reply message to {key}.'
                                logger.error(failed_send_autoreply)
                                print(failed_send_autoreply)
                                data_report.extend([report_time_start, report_time_stop, key, 'Error', failed_send_autoreply, ''])

                                # write failed send auto reply message to excel
                                fail_auto_reply_file = f'./report/reply_message/failed/send_auto_reply_message_{current_date}.xlsx'
                                insert_excel(data_report, fail_auto_reply_file)
                                logger.info('Successfully write failed send auto reply message to excel')
                                print('Successfully write failed send auto reply message to excel')

                                # write data auto reply message to txt file
                                auto_reply_report = f'./report/reply_message/failed/send_auto_reply_message_{current_date}.txt'
                                auto_reply_report_folder = Folder.is_exists(auto_reply_report)
                                if not auto_reply_report_folder:
                                    logger.info('Create folder for failed send auto reply message')
                                    print('Create folder for failed send auto reply message')
                                    Folder.mkdir(auto_reply_report)

                                auto_reply_report = open(auto_reply_report, 'a')  # append mode
                                auto_reply_report.write(f'{data_report[0]} | {time_start_autoreply} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {key} | Error | {failed_send_autoreply} | \n')
                                auto_reply_report.close()
                                logger.info('Successfully write failed send auto reply message to txt file')
                                print('Successfully write failed send auto reply message to txt file')

                                data_report.clear()
                                del time_start_autoreply, failed_send_autoreply, fail_auto_reply_file
                                # skip current iteration
                                continue

                            time.sleep(5)
                            # send message by press Enter
                            logger.info('Trying to send auto reply message')
                            print('Trying to send auto reply message')
                            input_box.send_keys(Keys.ENTER)

                            time_stop_autoreply = tools.get_datetime('%H:%M:%S')
                            time.sleep(1)
                            logger.info(f'Message auto_reply: {random_message}.')
                            print(f'Message auto_reply: {random_message}.')

                            try:
                                success_send_autoreply = f'Successfully get data reply message from {key}'
                                data_report.extend([report_time_start, time_stop_autoreply, key, 'Success', success_send_autoreply, random_message])

                                # write success get data reply message to excel
                                file_success = f'./report/reply_message/success/send_auto_reply_message_{current_date}.xlsx'
                                insert_excel(data_report, file_success)
                                logger.info('Successfully write success send auto reply message to excel')
                                print('Successfully write success send auto reply message to excel')

                                # write data auto reply message to txt file
                                auto_reply_report = f'./report/reply_message/success/send_auto_reply_message_{current_date}.txt'
                                auto_reply_report_folder = Folder.is_exists(auto_reply_report)
                                if not auto_reply_report_folder:
                                    logger.info('Create folder for success send auto reply message')
                                    print('Create folder for success send auto reply message')
                                    Folder.mkdir(auto_reply_report)

                                auto_reply_report = open(auto_reply_report, 'a')  # append mode
                                auto_reply_report.write(f'{data_report[0]} | {time_start_autoreply} | {time_stop_autoreply} | {HOST_NAME} - {IP_ADDRESS} | {key} | Success | {success_send_autoreply} | {random_message}\n')
                                auto_reply_report.close()
                                logger.info('Successfully write success send auto reply message to txt file')
                                print('Successfully write success send auto reply message to txt file')
                                
                                logger.info(f'Changing phone {key} to read')
                                dict_of_phone[key] = 'read'
                            except Exception as e:
                                logger.error('Error when program to write success send auto reply message. Error: {e}'.format(e=e))
                                logger.error(traceback.format_exc())
                                print(e)
                                continue

                        time.sleep(random.randint(5, 8))

                        # clear chat
                        # clear_chat(browser)
                        data_report.clear()
                    except Exception as e:
                        logger.error('Failed to get unread message. Error: {e}'.format(e=e))

        except Exception as e:
            logger.error('Failed to get data reply message. Error: {e}'.format(e=e))
            logger.error(traceback.format_exc())
            print('Failed to get data reply message')

            logger.info('Trying to stop the program')
            print('Trying to stop the program')
            sys.tracebacklimit = 0
            sys.exit(1)

        print(f'\nFinish checking reply message {type_log_msg}')
        logger.info(f'Finish checking reply message {type_log_msg}')                
    

@csrf_exempt
def bulk_send_v3(request):
    if request.method == 'POST': 
        data = request.POST
        files = request.FILES
        
        instance = data.get('instance', '')
        instance = instance.strip()
        if not instance:
            logger.warning('Instance browser is empty.')
            print('No instance found')

            del instance

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': 'Instance is required'
                }), headers=headers, status=400
            )
        
        # get driver browser from instance id
        browser = active_sessions.get(instance, None)
        if not browser:
            logger.error(f'No active instance browser {instance} found.')
            print('No active instance found')

            del browser

            return HttpResponse(
                json.dumps({
                    'status': 'error',
                    'message': f'No active instance with instance id {instance} found'.format(instance=instance)
                }), headers=headers, status=400
            )

        required_files = ['phone_list_file', 'dialogue_file', 'soceng_file', 'message_file', 'opening_decorator', 'opening_message', 'closing_message', 'closing_decorator']
        optional_files = ['auto_reply_file']

        # Check if required files are present and have valid format
        for file_name in required_files:
            file = files.get(file_name)
            if not file:
                logger.warning(f'{file_name} is empty')
                print(f'{file_name} is empty')

                del file

                return HttpResponse(
                    json.dumps({
                        'status': 'error',
                        'message': f'{file_name} is required'
                    }), headers=headers, status=400
                )

            if not file.name.endswith('.txt'):
                logger.warning('Invalid file format. Only .txt files are allowed')
                print('Invalid file format. Only .txt files are allowed')

                del file

                return HttpResponse(
                    json.dumps({
                        'status': 'error',
                        'message': 'Invalid file format. Only .txt files are allowed'
                    }), headers=headers, status=400
                )

        # Check optional files for valid format
        for file_name in optional_files:
            file = files.get(file_name)
            if file:
                if not file.name.endswith('.txt'):
                    logger.warning(f'Invalid file format for {file_name}. Only .txt files are allowed')
                    print(f'Invalid file format for {file_name}. Only .txt files are allowed')

                    del file

                    return HttpResponse(
                        json.dumps({
                            'status': 'error',
                            'message': f'Invalid file format for {file_name}. Only .txt files are allowed'
                        }), headers=headers, status=400
                    )

        phone_list_file = files['phone_list_file']
        soceng_file = files['soceng_file']
        dialogue_file = files['dialogue_file']
        message_file = files['message_file']
        auto_reply_file = files['auto_reply_file']
        opening_decorator_file = files['opening_decorator']
        opening_message_file = files['opening_message']
        closing_message_file = files['closing_message']
        closing_decorator_file = files['closing_decorator']

        # Check if file is present and has valid content
        if opening_decorator_file.size == 0:
            logger.warning('Opening decorator file is empty')
            print('Opening decorator file is empty')
            opening_decorator_file = None

        if opening_message_file.size == 0:
            logger.warning('Opening message file is empty')
            print('Opening message file is empty')
            opening_message_file = None

        if closing_decorator_file.size == 0:
            logger.warning('Closing decorator file is empty')
            print('Closing decorator file is empty')
            closing_decorator_file = None

        if closing_message_file.size == 0:
            logger.warning('Closing message file is empty')
            print('Closing message file is empty')
            closing_message_file = None

        if soceng_file.size == 0:
            logger.warning('Soceng file is empty')
            print('Soceng file is empty')
            soceng_file = None

        if dialogue_file.size == 0:
            logger.warning('Dialogue file is empty')
            print('Dialogue file is empty')
            dialogue_file = None

        # default start interval random value is 10800s (3h)
        start_interval = int(os.getenv('START_INTERVAL', '10800'))
        start_value = data.get('start_interval', '')
        start_value = start_value.strip()
        if start_value:
            start_interval = int(start_value)

        # default end interval random value is 18000s (5h)
        end_interval = int(os.getenv('END_INTERVAL', '18000'))
        end_value = data.get('end_interval', '')
        end_value = end_value.strip()
        if end_value:
            end_interval = int(end_value)

        # default random value for start interval dialogue is 300s (5m)
        dialogue_start_interval = int(os.getenv('DEFAULT_DIALOGUE_START_INTERVAL', '300'))
        dialogue_start = data.get('dialogue_start_interval', '')
        dialogue_start = dialogue_start.strip()
        if dialogue_start:
            dialogue_start_interval = int(dialogue_start)

        # default random value for end interval dialogue is 900s (15m)
        dialogue_end_interval = int(os.getenv('DEFAULT_DIALOGUE_END_INTERVAL', '900'))
        dialogue_end = data.get('dialogue_end_interval', '')
        dialogue_end = dialogue_end.strip()
        if dialogue_end:
            dialogue_end_interval = int(dialogue_end)

        # default random value for start interval soceng is 6s
        soceng_start_interval = int(os.getenv('RANDOM_SOCENG_START_INTERVAL', '15'))
        soceng_start = data.get('soceng_start_interval', '')
        soceng_start = soceng_start.strip()
        if soceng_start:
            soceng_start_interval = int(soceng_start)

        # default random value for end interval dialogue is 12s
        soceng_end_interval = int(os.getenv('RANDOM_SOCENG_END_INTERVAL', '30'))
        soceng_end = data.get('soceng_end_interval', '')
        soceng_end = soceng_end.strip()
        if soceng_end:
            soceng_end_interval = int(soceng_end)

        # default total message of interval is 400
        total_message_min = int(os.getenv('DEFAULT_TOTAL_MESSAGE_MIN', '10'))
        message_count_min = data.get('total_message_interval_min', '')
        message_count_min = message_count_min.strip()
        if message_count_min:
            total_message_min = int(message_count_min)
            
        # default total message of interval is 400
        total_message_max = int(os.getenv('DEFAULT_TOTAL_MESSAGE_MAX', '20'))
        message_count_max = data.get('total_message_interval_max', '')
        message_count_max = message_count_max.strip()
        if message_count_max:
            total_message_max = int(message_count_max)
        
        # default timeout is 30s
        timeout = int(os.getenv('DEFAULT_TIMEOUT', '30'))
        timeout_interval = data.get('timeout', '')
        timeout_interval = timeout_interval.strip()
        if timeout_interval:
            timeout = int(timeout_interval)

        browser.switch_to.window(browser.window_handles[0])
        handles = browser.window_handles
        for _, handle in enumerate(handles):
            if handle != browser.current_window_handle:
                browser.switch_to.window(handle)
                browser.close()

        browser.switch_to.window(browser.window_handles[0])
        event = Event()

        message_index = 0
        opening_decorator_idx = 0
        opening_msg_idx = 0
        closing_decorator_idx = 0
        closing_msg_idx = 0

        # limit message wa
        message_limit = 0
        total_message_limit_first = int(os.getenv('TOTAL_BLAST_MIN', '900'))
        total_message_limit_last = int(os.getenv('TOTAL_BLAST_MAX', '999'))
        random_message_limit = random.randint(total_message_limit_first, total_message_limit_last)

        msg_limit_file = open(f'log/tmp_message_limit.txt', 'w')
        msg_limit_file.write(str(0))
        msg_limit_file.close

        send_soceng_message = data.get('send_soceng_message', '')
        send_soceng_message = send_soceng_message.strip().lower()
        if send_soceng_message == 'true':
            send_soceng_message = True
        else:
            send_soceng_message = False

        send_dialogue_message = data.get('send_dialogue_message', '')
        send_dialogue_message = send_dialogue_message.strip().lower()
        if send_dialogue_message == 'true':
            send_dialogue_message = True
        else:
            send_dialogue_message = False

        # read phone number file
        files = pd.read_csv(phone_list_file, header=None, names=['phone'], chunksize=1)

        logger.info(f"""start_interval: {start_interval}, end_interval: {end_interval},
                    soceng_start_interval: {soceng_start_interval}, soceng_end_interval: {soceng_end_interval},
                    dialogue_start_interval: {dialogue_start_interval}, dialogue_end_interval: {dialogue_end_interval},
                    total_message_min: {total_message_min}, total_message_max: {total_message_max}, timeout: {timeout}, total_message_limit: {random_message_limit}
                    send_soceng_message: {send_soceng_message}, send_dialogue_message: {send_dialogue_message}""")

        is_auto_reply = data.get('is_auto_reply', '')
        is_auto_reply = is_auto_reply.strip().lower()
        if is_auto_reply == 'true':
            is_auto_reply = True
        else:
            is_auto_reply = False

        # Check if auto_reply_file size is empty
        if auto_reply_file.size == 0:
            logger.warning('Auto reply file is empty')
            auto_reply_file = None

        # Check reply message before start blast
        logger.info('Trying to read input file for auto reply')
        print('Trying to read input file for auto reply')
        input_data = pd.read_csv(auto_reply_file, header=None, names=['message']) if auto_reply_file else None
        
        #auto_reply_message(browser, input_data, auto_reply_conf=is_auto_reply, type_log_msg='before start blast')

        df_message = pd.read_csv(message_file, header=None)
        df_opening_decorator = pd.read_csv(opening_decorator_file, header=None) if opening_decorator_file else None
        df_opening_message = pd.read_csv(opening_message_file, header=None) if opening_message_file else None
        df_closing_message = pd.read_csv(closing_message_file, header=None) if closing_message_file else None
        df_closing_decorator = pd.read_csv(closing_decorator_file, header=None) if closing_decorator_file else None

        total_row_opening_decorator = len(df_opening_decorator) if df_opening_decorator is not None else 0
        total_row_opening_message = len(df_opening_message) if df_opening_message is not None else 0
        total_row_closing_message = len(df_closing_message) if df_closing_message is not None else 0
        total_row_closing_decorator = len(df_closing_decorator) if df_closing_decorator is not None else 0

        check_reply_interval_min = data.get('auto_reply_check_interval', '')
        check_reply_interval_max = data.get('auto_reply_check_interval_max', '')
        check_reply_interval_min = check_reply_interval_min.strip()
        check_reply_interval_max = check_reply_interval_max.strip()
        # add a counter to check reply message
        message_counter = 0
        # if check_reply_interval is not empty, convert to integer
        if check_reply_interval_min:
            check_reply_interval_min = int(check_reply_interval_min)
        if check_reply_interval_min:
            check_reply_interval_max = int(check_reply_interval_max)

        check_reply_interval = random.randint(check_reply_interval_min, check_reply_interval_max)

        # timeout counter for blast message
        timeout_counter = 0

        # refresh browser every params refresh_browser_count or 100 messages by default
        refresh_count = data.get('refresh_browser_count', '')
        if refresh_count:
            refresh_count = int(refresh_count)
        else:
            refresh_count = int(os.getenv('REFRESH_BROWSER_COUNT', '100'))

        # maximum retries
        max_retries = 1

        logger.info(f'auto_reply_check_interval: {check_reply_interval}, refresh_browser_count: {refresh_count}, is_auto_reply: {is_auto_reply}')

        print('\nStart processing bulk send whatsapp...')
        logger.info('Start processing bulk send whatsapp.')
        # iterate the target number in array phone list
        random_seed = int(datetime.now().timestamp())
        random.seed(random_seed)
        logger.info(f'Using Random Seed {random_seed}')
        phone_sent = {}
        cnt = 0
        total_message = 0
        for chunk in files:          
            for index, row in chunk.iterrows():
                if cnt == 0:
                    total_message = random.randint(total_message_min, total_message_max)
                    logger.info(f'Random Total Message: {total_message}')
                cnt += 1     
                phone = row['phone']
                data_report = tools.get_datetime('%Y-%m-%d')
                time_start = time.perf_counter()

                msg_limit_file = open(f'log/tmp_message_limit.txt', 'r')
                tmp_msg_limit = msg_limit_file.read()
                msg_limit_file.close

                # set default tmp_msg_limit to message_limit if msg_limit_file is empty
                if not tmp_msg_limit:
                    tmp_msg_limit = message_limit

                message_limit = int(tmp_msg_limit)

                # stop blast message when process send message reach random_message_limit
                if message_limit == random_message_limit or message_limit > random_message_limit:
                    print(f'----| Total message limit is reached')
                    logger.info(f'Total message limit is reached')

                    # stop the program when total message limit is reached
                    print('----| Trying to stop the program')
                    logger.info('Trying to stop the program')
                    sys.tracebacklimit=0
                    sys.exit(0)

                print(f'\n{tools.get_datetime("%d-%m-%Y %H:%M:%S")}')
                print(f'{index + 1}. Trying to send message to {phone}')
                logger.info(f'{index + 1}. Trying to send message to {phone}')

                report_time_start = tools.get_datetime('%H:%M:%S')
                # check format phone number
                phone = str(phone)
                phone = phone.strip()
                phone_number = check_format_number(phone)
                report_time_stop = tools.get_datetime('%H:%M:%S')
                # skip iteration if result from check_format_number is empty
                if not phone_number:
                    invalid_no_message = f'Incorrect format mobile phone number: {phone}'
                    print(invalid_no_message)
                    logger.error(invalid_no_message)

                    # write failed send message phone number to txt file
                    failed_number = f'./report/send/failed/failed_send_{current_date}.txt'
                    report_file_folder = Folder.is_exists(failed_number)
                    if not report_file_folder:
                        logger.info('Create folder for failed send message')
                        print('Create folder for failed send message')
                        Folder.mkdir(failed_number)

                    report_file = open(failed_number, 'a')  # append mode
                    report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {invalid_no_message}\n')
                    logger.info('Successfully write failed send message to txt file')
                    print('Successfully write failed send message to txt file')

                    del time_start, failed_number, invalid_no_message, failed_number, report_time_start, report_time_stop, phone_number, phone
                    del data_report, time_start, msg_limit_file, tmp_msg_limit, message_limit
                    # skip current iteration
                    continue

                if event.is_set():
                    logger.info('Event is set. Stop the process blast message')
                    print('Event is set. Stop the process blast message')
                    Browser.close_tab(browser)

                handles = len(browser.window_handles)
                if handles == 1:
                    # open new tab
                    Browser.new_tab(browser)

                # refresh browser base on params input or by default every 100 messages
                if index % refresh_count == 0 and index > 0:
                    # refresh browser
                    logger.info(f'Trying to refresh browser')
                    print(f'----| Trying to refresh browser')
                    browser.refresh()
                    time.sleep(5)

                    try:
                        WebDriverWait(browser, timeout).until(lambda driver: (
                            element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
                        ))
                    except TimeoutException:
                        logger.error('Timeout error waiting for page to load chat after refresh browser.')
                        logger.error(traceback.format_exc())
                        print('----| Timeout error waiting for page to load chat after refresh browser.')

                        # stop the program when timeout
                        logger.info('Trying to stop the program')
                        print('----| Trying to stop the program')
                        sys.exit(1)


                # open chat URL to this number and wait for window/chats to load
                for i in range(max_retries):
                    try:
                        logger.info(f'Open chat URL to send message to {phone_number}.')
                        print(f'----| Open chat URL to send message to {phone_number}.')
                        browser.get(CHAT_URL.format(phone=phone_number))
                        time.sleep(6)

                        logger.info('Waiting for page to load chat')
                        print('----| Waiting for page to load chat')
                        # check if the page is loaded
                        WebDriverWait(browser, timeout).until(lambda driver: (
                            element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
                        ))

                        # if the page is loaded then break the loop
                        break
                    except TimeoutException:
                        report_time_stop = tools.get_datetime('%H:%M:%S')
                        timeout_msg = f'Timeout error waiting for page to load chat from {phone_number}.'
                        logger.error(timeout_msg)
                        logger.error(traceback.format_exc())
                        print(f'----| {timeout_msg}')

                        # write timeout phone number to txt file
                        file_timeout_number = f'./report/send/timeout/timeout_send_{current_date}.txt'
                        report_file_folder = Folder.is_exists(file_timeout_number)
                        if not report_file_folder:
                            logger.info('Create folder for timeout phone number')
                            print('----| Create folder for timeout phone number')
                            Folder.mkdir(file_timeout_number)

                        # single_line_msg = message.replace('\n', '\\n')
                        report_file = open(file_timeout_number, 'a')  # append mode
                        report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {timeout_msg} | {message}\n')
                        report_file.close()
                        logger.info('Successfully write timeout phone number to txt file')
                        print('----| Successfully write timeout phone number to txt file')

                        logger.error(f'Timeout error waiting for page to load chat. Attempt {i+1} of {max_retries}')
                        print(f'----| Timeout error waiting for page to load chat. Attempt {i+1} of {max_retries}')
                        if i == max_retries - 1:  # if this was the last attempt
                            # upload report to server
                            thread = Thread(target=sync_report)
                            thread.start()
                            thread.join()  # Wait for the thread to finish

                            raise  # re-raise the last exception

                        # refresh browser
                        logger.info('Trying to refresh browser')
                        print('----| Trying to refresh browser')
                        time.sleep(4)
                    except Exception as e:
                        logger.error(f'Error waiting for page to load chat. Error: {e}')
                        logger.error(traceback.format_exc())
                        print(f'----| Error waiting for page to load chat. Error: {e}')

                time.sleep(3)

                # dynamic blast message
                # get next message
                loopevery = 20
                if index % loopevery == 0:
                    opening_decorator_idx = random.randint(1, df_opening_decorator.shape[0]) if opening_decorator_file is not None else 0
                    opening_msg_idx = random.randint(1, df_opening_message.shape[0]) if opening_message_file is not None else 0
                    message_index = random.randint(1, df_message.shape[0]) if message_file is not None else 0
                    closing_msg_idx = random.randint(1, df_closing_message.shape[0]) if closing_message_file is not None else 0
                    closing_decorator_idx = random.randint(1, df_closing_decorator.shape[0]) if closing_decorator_file is not None else 0
                
                if index + 1 > 1 and total_message > 0:        
                    opening_decorator_idx = opening_decorator_idx + 1
                    opening_msg_idx = opening_msg_idx + 1
                    message_index = message_index + 1
                    closing_msg_idx = closing_msg_idx + 1
                    closing_decorator_idx = closing_decorator_idx + 1

                # reset message to beginning
                if message_index >= df_message.shape[0]:
                    message_index = 0

                if opening_decorator_idx >= total_row_opening_decorator:
                    opening_decorator_idx = 0

                if opening_msg_idx >= total_row_opening_message:
                    opening_msg_idx = 0

                if closing_msg_idx >= total_row_closing_message:
                    closing_msg_idx = 0

                if closing_decorator_idx >= total_row_closing_decorator:
                    closing_decorator_idx = 0
                    

                opening_decorator = df_opening_decorator[0][opening_decorator_idx] if opening_decorator_file is not None else ''
                opening_message = df_opening_message[0][opening_msg_idx] if opening_message_file is not None else ''
                message = df_message[0][message_index] if message_file is not None else ''
                closing_message = df_closing_message[0][closing_msg_idx] if closing_message_file is not None else ''
                closing_decorator = df_closing_decorator[0][closing_decorator_idx] if closing_decorator_file is not None else ''
                
                logger.info(f'Selecting opening_decorator_idx {opening_decorator_idx}, message: {opening_decorator}')
                logger.info(f'Selecting opening_message_idx {opening_msg_idx}, message: {opening_message}')
                logger.info(f'Selecting message {message_index}, message: {message}')
                logger.info(f'Selecting closing_message {closing_msg_idx}, message: {closing_message}')
                logger.info(f'Selecting closing_decorator_idx {closing_decorator_idx}, message: {closing_decorator}')

                # Remove empty string from the list
                list_message = [opening_decorator, opening_message, message, closing_message, closing_decorator]
                messages = [msg_item for msg_item in list_message if msg_item != '']
                # Join the variables with a new line
                combined_message = '\n\n'.join(messages)
                # single_line_combined_msg = combined_message.replace('\n', '\\n')

                is_success = True
                for i in range(max_retries):
                    try:
                        # find text input box
                        logger.info('Trying to find text input box')
                        print('----| Trying to find text input box')
                        time.sleep(10)
                        input_box = WebDriverWait(browser, 120).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
                        )
                        logger.info(f'Trying write message to text input box')
                        print(f'----| Trying write message to text input box')
                        # paste_text(browser, input_box, combined_message)
                        for line in combined_message.splitlines():
                            stoppage_line = random.randint(10, 20)
                            logger.info(f'Pause every {stoppage_line} character')
                            for idx, word in enumerate(line):
                                if ((idx+1) % stoppage_line) == 0:
                                    time.sleep(random.randint(5, 10))
                                input_box.send_keys(word)
                                time.sleep(.3)
                            #input_box.send_keys(line)
                            time.sleep(1)
                            input_box.send_keys(Keys.SHIFT, Keys.ENTER)

                        time.sleep(10)

                        # send message by press Enter
                        logger.info(f'Trying to send message')
                        print(f'----| Trying to send message')
                        # re-locate the input_box before interacting with it
                        input_box = WebDriverWait(browser, 120).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
                        )
                        input_box.send_keys(Keys.ENTER)
                        report_time_stop = tools.get_datetime('%H:%M:%S')

                        time.sleep(random.randint(4, 7))

                        # re-locate the input_box before interacting with it
                        input_box = WebDriverWait(browser, 120).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
                        )
                        input_box.send_keys(Keys.ESCAPE)

                        # if the page is loaded then break the loop
                        break
                    except TimeoutException:
                        report_time_stop = tools.get_datetime('%H:%M:%S')
                        timeout_msg = f'The message to {phone_number} could not be sent because the connection timed out.'
                        logger.error(timeout_msg)
                        logger.error(traceback.format_exc())
                        print(f'----| {timeout_msg}')

                        # write timeout phone number to txt file
                        file_timeout_number = f'./report/send/timeout/timeout_send_{current_date}.txt'
                        report_file_folder = Folder.is_exists(file_timeout_number)
                        if not report_file_folder:
                            logger.info('Create folder for timeout phone number')
                            print('----| Create folder for timeout phone number')
                            Folder.mkdir(file_timeout_number)

                        report_file = open(file_timeout_number, 'a')  # append mode
                        report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {timeout_msg} | {combined_message}\n')
                        report_file.close()
                        logger.info('Successfully write timeout phone number to txt file')
                        print('----| Successfully write timeout phone number to txt file')

                        logger.error(f'Timeout error waiting for page to load chat. Attempt {i+1} of {max_retries}')
                        print(f'----| Timeout error waiting for page to load chat. Attempt {i+1} of {max_retries}')
                        if i == max_retries - 1:  # if this was the last attempt
                            # upload report to server
                            thread = Thread(target=sync_report)
                            thread.start()
                            thread.join()  # Wait for the thread to finish

                            raise  # re-raise the last exception

                        # refresh browser
                        logger.info(f'Trying to refresh browser for send message to {phone_number}.')
                        print(f'----| Trying to refresh browser for send message to {phone_number}.')
                        time.sleep(3)
                        browser.refresh()
                        time.sleep(5)
                        browser.get(CHAT_URL.format(phone=phone_number))
                        time.sleep(6)
                    except Exception as e:
                        is_success = False
                        failed_sending_msg = f'Failed send message to {phone_number}.'
                        logger.error(f'{failed_sending_msg}. Error: {e}')
                        logger.error(traceback.format_exc())
                        print(f'----| {failed_sending_msg}')

                        # write failed send message phone number to txt file
                        failed_number = f'./report/send/failed/failed_send_{current_date}.txt'
                        report_file_folder = Folder.is_exists(failed_number)
                        if not report_file_folder:
                            logger.info('Create folder for failed send message')
                            print('----| Create folder for failed send message')
                            Folder.mkdir(failed_number)

                        report_file = open(failed_number, 'a')  # append mode
                        report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {failed_sending_msg} | {combined_message}\n')
                        report_file.close()
                        logger.info('Successfully write failed send message to txt file')
                        print('----| Successfully write failed send message to txt file')

                        # skip current iteration
                        # continue

                        # stop the program when failed to send message
                        logger.info('Trying to stop the program')
                        print('----| Trying to stop the program')
                        sys.exit(1)

                if is_success:
                    success_sending_msg = f'Successfully sending message to {phone_number}'
                    logger.info(success_sending_msg)
                    print(f'----| {success_sending_msg}')
                    logger.info(f'Message blast: \n{combined_message}')
                    print(f'----| Message blast: \n{combined_message}')

                    # write timeout phone number to txt file
                    success_number = f'./report/send/success/success_send_{current_date}.txt'
                    report_file_folder = Folder.is_exists(success_number)
                    if not report_file_folder:
                        logger.info('Create folder for success send message')
                        print('----| Create folder for success send message')
                        Folder.mkdir(success_number)

                    report_file = open(success_number, 'a')  # append mode
                    report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Success | {success_sending_msg} | {combined_message}\n')
                    report_file.close()
                    logger.info('Successfully write success send message to txt file')
                    print('----| Successfully write success send message to txt file')

                    message_limit = message_limit + 1
                    msg_limit_file = open(f'log/tmp_message_limit.txt', 'w')
                    msg_limit_file.write(str(message_limit))
                    msg_limit_file.close

                    msg_limit_file = open(f'log/tmp_message_limit.txt', 'r')
                    tmp_msg_limit = msg_limit_file.read()
                    msg_limit_file.close

                # measure sending message time
                time_end = time.perf_counter() - time_start
                print(f'----| It takes {time_end:.2f}s for sending message to {phone_number}')

                # if success sending message, start checking reply message in interval message
                if is_success:
                    phone_sent[phone_number] = 'unread'
                    message_counter += 1
                    if check_reply_interval and message_counter % check_reply_interval == 0:
                        # start checking reply message in interval message
                        # auto_reply_message(browser, input_data, auto_reply_conf=is_auto_reply, type_log_msg='in interval message')
                        auto_reply_message_v2(browser, input_data, phone_sent, auto_reply_conf=is_auto_reply, type_log_msg='in interval message')

                # set interval time after reaching of total messages
                logger.info(f'Now at Message {cnt} out of {total_message} before ngasoh')
                if cnt % total_message == 0 and index > 0 and cnt > 0:
                    # delete the group chat before the social engineering process program begins
                    # logger.info('Delete group chat before the dialogue process program begins')
                    # print('----| Delete group chat before the dialogue process program begins')
                    # threads_group_chat = Thread(target=clear_all_group_chat, args=(browser,))
                    # logger.info('Start thread clear group chat')
                    # threads_group_chat.start()
                    # wait for thread clear group chat to finish
                    # logger.info('Wait for thread clear group chat to finish')
                    # threads_group_chat.join()
                    # del threads_group_chat

                    interval = random.randint(start_interval, end_interval)
                    print(f'----| Wait for {interval}s to send the next message')
                    items = list(range(interval, 0, -1))

                    if send_dialogue_message:
                        dialogue_file.file.seek(0)
                        logger.info('Start dialogue chat')
                        print('----| Start dialogue chat')
                        threads = Thread(target=dialogue_v3, args=(browser, dialogue_file, dialogue_start_interval, dialogue_end_interval, timeout, event, message_limit, random_message_limit, 'dialogue'))
                        logger.info('Start thread dialogue chat')
                        threads.start()

                        if event.is_set():
                            logger.error('Stop the process blast message')
                            print('Stop the process blast message')
                            sys.tracebacklimit=0
                            sys.exit(0)

                    print('\n\n')
                    
                    close_tab = random.randint(0, 1)
                    
                    logger.info(f'Program decided to close the tab')
                    if close_tab == 1:
                    
                        logger.info(f'Closing Tab')
                        time.sleep(10)
                        print('tab closing')
                        Browser.close_tab(browser)
                        logger.info(f'Start Counting')
                    
                    logger.info(f'Start ngasoh at {datetime.now().timestamp()}')
                    for _ in countdown(items, prefix = 'Next blast message in:'):
                        time.sleep(1)
                    cnt = 0
                    
                    logger.info(f'Finish ngasoh at {datetime.now().timestamp()}')
                    
                    if close_tab == 1:
                        print('tab opening')
                        Browser.new_tab(browser)
                        browser.get(BASE_URL)
                        
                        time.sleep(15)
                        print('tab should be open now')

                    if send_dialogue_message:
                        # stop dialogue chat when no interval blast message
                        logger.info('Stop dialogue chat when no interval blast message')
                        event.set()
                        # wait for new thread to finish
                        logger.info('Wait for thread dialogue chat to finish')
                        threads.join()
                        # reset event to false
                        event.clear()

                else:
                    if send_soceng_message:
                        soceng_file.file.seek(0)
                        logger.info('Start social engineering')
                        print('\n----| Start social engineering')
                        threads = Thread(target=dialogue_v3, args=(browser, soceng_file, soceng_start_interval, soceng_end_interval, timeout, event, message_limit, random_message_limit, 'soceng'))
                        logger.info('Start thread social engineering')
                        threads.start()
                    else:
                        task_start = int(os.getenv('WAIT_NEXT_TASK_START', '120'))
                        task_end = int(os.getenv('WAIT_NEXT_TASK_END', '225'))
                        random_number = random.randint(task_start, task_end)
                        print(f'----| Rest in {random_number}s')
                        logger.info(f'Rest in {random_number}s')
                        time.sleep(random_number)

                    if send_soceng_message:
                        # stop social engineering when program interval blast message is complete
                        # event.set() # change stop soceng process in soceng or dialogue
                        # wait for new thread to finish
                        logger.info('Wait for thread social engineering to finish')
                        threads.join()

                        if event.is_set():
                            logger.error('Stop the process blast message')
                            print('Stop the process blast message')
                            logger.debug(traceback.format_exc())
                            sys.tracebacklimit=0
                            sys.exit(1)

                        # reset event to false
                        logger.info('Reset event to false')
                        event.clear()

                # del is_success, threads

        #auto_reply_message(browser, input_data, auto_reply_conf=is_auto_reply, type_log_msg='after blast')
        auto_reply_message_v2(browser, input_data, phone_sent, auto_reply_conf=is_auto_reply, type_log_msg='after blast')

        # Upload report to server
        thread = Thread(target=sync_report)
        thread.start()
        thread.join()  # Wait for the thread to finish

        del data, files, instance, browser
        logger.info('Successfully sending bulk message')
        print('\nSuccessfully sending bulk message\n')
        return HttpResponse(
            json.dumps({
                'status': 'success',
                'message': 'Bulk message sent successfully'
            }),
            headers=headers,
            status=200
        )

    else:
        return HttpResponse(status=405)

def dialogue_v3(browser, file_path, start_interval, end_interval, timeout, event, message_limit, random_message_limit, chat_type = 'dialogue'):
    if not file_path:
        print(f'\nFile text for {chat_type} is not found')
        logger.info(f'File text for {chat_type} is not found.')
        del chat_type

        return None

    handles = len(browser.window_handles)
    if handles == 1:
        # open new tab
        Browser.new_tab(browser)

    # random 15 - 30 seconds
    random_sleep = random.randint(start_interval, end_interval)
    logger.info(f'Wait in {random_sleep}s before start {chat_type}')
    print(f'----| Wait in {random_sleep}s before start {chat_type}')
    time.sleep(random_sleep)

    # read phone number file
    logger.info(f'Trying to read phone number file for {chat_type}')
    print(f'\nTrying to read phone number file for {chat_type}')
    # read the entire file
    dataframe = pd.read_csv(file_path, header=None, names=['phone', 'message'], delimiter='|')

    # load txt files tmp soceng message send
    tmp_soceng_send = f'log/tmp_{chat_type}_send.txt'
    df_tmp_soceng_send = pd.read_csv(tmp_soceng_send, header=None, names=['phone', 'message'], delimiter='|')
    tmp_soceng = pd.read_csv(tmp_soceng_send, header=None, names=['phone', 'message'], delimiter='|')
    # define the column to compare
    key_column = 'message'
    # find the rows in dataframe that are not in tmp_soceng
    new_df = dataframe[~dataframe[key_column].isin(tmp_soceng[key_column])]

    # Clear the file 'log/tmp_soceng_send.txt' or 'log/tmp_dialogue_send.txt' when the total message is less than 2
    if (len(dataframe) - len(df_tmp_soceng_send)) <= 2:
        # join the new dataframe with the old dataframe
        # new_df = pd.concat([new_df, dataframe], ignore_index=True)

        with open(tmp_soceng_send, 'w') as file:
            file.write('')

    # Shuffle the DataFrame
    num_rows = random.randint(1, 2)
    random_df = new_df.sample(n=num_rows).reset_index(drop=True)
    
    # Sequential the DataFrame
    # random_df = new_df.iloc[:num_rows]

    # timeout counter for dialogue message
    # timeout_counter = 0

    # maximum retry
    max_retry = int(os.getenv('MAX_RETRY', '3'))

    print(f'\n\n\nStart processing {num_rows} {chat_type}...')
    logger.info(f'Start processing {num_rows} {chat_type}')

    # iterate the target number in array phone list
    for index, row in random_df.iterrows():
        # check if the event is set
        if event.is_set():
            # if the event is set then stop soceng process
            break

        phone = row['phone']
        if pd.isna(phone):
            phone = ''

        message = row['message']
        if pd.isna(message):
            message = ''

        msg_limit_file = open(f'log/tmp_message_limit.txt', 'r')
        tmp_msg_limit = msg_limit_file.read()
        msg_limit_file.close

        # set default tmp_msg_limit to message_limit if msg_limit_file is empty
        if not tmp_msg_limit or int(tmp_msg_limit) == 0:
            tmp_msg_limit = message_limit

        msg_limit = int(tmp_msg_limit)

        # stop soceng when process total sending message reach random_message_limit
        if msg_limit == random_message_limit:
            print(f'----| Total message limit {chat_type} is reached')
            logger.info(f'Total message limit {chat_type} is reached')

            del msg_limit_file, tmp_msg_limit, msg_limit

            # stop soceng process
            event.set()
            # break

        # check if the event is set
        if event.is_set():
            logger.info(f'Event is set. Stop the process {chat_type}')

            # if the event is set then stop soceng process
            # break
            logger.info(f'Stop the process {chat_type}')
            print(f'----| Stop the process {chat_type}')
            sys.exit(1)

        time_start = time.perf_counter()
        print(f'\n{tools.get_datetime("%d-%m-%Y %H:%M:%S")}')
        print(f'{index + 1}. Trying to {chat_type} with number {phone}')
        logger.info(f'{index + 1}. Trying to {chat_type} with number {phone}')

        handles = len(browser.window_handles)
        if handles == 1:
            # open new tab
            Browser.new_tab(browser)

        data_report = tools.get_datetime('%Y-%m-%d')
        report_time_start = tools.get_datetime('%H:%M:%S')

        # check format phone number
        phone = str(phone)
        phone = phone.strip()
        phone_number = check_format_number(phone)
        # skip iteration if result from check_format_number is empty
        if not phone_number:
            report_time_stop = tools.get_datetime('%H:%M:%S')
            incorrect_no_msg = f'Incorrect format mobile phone number: {phone}.'
            print(incorrect_no_msg)
            logger.error(incorrect_no_msg)

            # write invalid phone number to txt file
            file_invalid_number = f'./report/{chat_type}/invalid/invalid_number_{chat_type}_{current_date}.txt'
            report_file_folder = Folder.is_exists(file_invalid_number)
            if not report_file_folder:
                logger.info('Create folder for invalid number report')
                print('----| Create folder for invalid number report')
                Folder.mkdir(file_invalid_number)

            report_file = open(file_invalid_number, 'a')  # append mode
            report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {incorrect_no_msg}\n')
            report_file.close()
            logger.info(f'Write invalid phone number to txt file')
            print(f'----| Write invalid phone number to txt file')

            del time_start, file_invalid_number, report_time_stop, incorrect_no_msg, phone_number, phone, handles, report_file
            # skip current iteration
            continue

        # single_line_msg = message.replace('\n', '\\n')

        # open chat URL to this number and wait for window/chats to load
        for i in range(max_retry):
            try:
                logger.info(f'Open chat URL to this number {phone_number}.')
                print(f'----| Open chat URL to this number {phone_number}.')
                browser.get(CHAT_URL.format(phone=phone_number))
                time.sleep(7)

                logger.info(f'Waiting for page to load chat from {phone_number}.')
                logger.info(f'Trying to find search bar element to check conversation header')
                print(f'----| Trying to find search bar element to check conversation header')
                WebDriverWait(browser, 120).until(lambda driver: (
                    element_exists(browser, By.CSS_SELECTOR, Selectors.SEARCH_BAR)
                ))
                time.sleep(2)

                # if the page is loaded then break the loop
                break
            except TimeoutException:
                report_time_stop = tools.get_datetime('%H:%M:%S')
                timeout_msg = f'Timeout error waiting for page to load chat.'
                print(timeout_msg)
                logger.error(timeout_msg)
                logger.error(traceback.format_exc())

                # write timeout phone number to txt file
                file_timeout_number = f'./report/{chat_type}/timeout/timeout_{chat_type}_{current_date}.txt'
                report_file_folder = Folder.is_exists(file_timeout_number)
                if not report_file_folder:
                    logger.info('Create folder for timeout report')
                    print('----| Create folder for timeout report')
                    Folder.mkdir(file_timeout_number)

                report_file = open(file_timeout_number, 'a')  # append mode
                report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {timeout_msg} | {message}\n')
                report_file.close()
                logger.info(f'Write timeout phone number to txt file')
                print(f'----| Write timeout phone number to txt file')

                logger.error(f'Timeout error waiting for page to load chat. Attempt {i+1} of {max_retry}')
                print(f'----| Timeout error waiting for page to load chat. Attempt {i+1} of {max_retry}')
                if i == max_retry - 1:  # if this was the last attempt
                    # upload report to server
                    thread = Thread(target=sync_report)
                    thread.start()
                    thread.join()  # Wait for the thread to finish

                    event.set()
                    raise # re-raise the last exception

                # refresh browser
                logger.info('Trying to refresh browser')
                print('----| Trying to refresh browser')
                time.sleep(3)
                browser.refresh()
                time.sleep(5)

                # if timeout greater than 5 than stop the process
                # timeout_counter += 1
                # if timeout_counter > 5:
                #     logger.info(f'Stopping the process {chat_type}. Timeout is greater than 5.')
                #     print(f'----| Stopping the process {chat_type}. Timeout is greater than 5.')

                #     # upload report to server
                #     thread = Thread(target=sync_report)
                #     thread.start()
                #     thread.join()  # Wait for the thread to finish
                #     break

            except Exception as e:
                logger.error(f'Error when trying to check conversation header. Error: {e}')
                logger.error(traceback.format_exc())
                print('----| Error when trying to check conversation header')
                logger.info('Trying to stop the program')
                print('----| Trying to stop the program')

                event.set()
                sys.exit(1)

        time.sleep(random.randint(4, 7))
        is_success = True
        # Check conversation header to identify phone number is valid
        try:
            lang_element = browser.find_element(By.CSS_SELECTOR, 'html').get_attribute('lang')
            logger.info(f'This WhatsApp web uses language: {lang_element}')
            conv_header = Selectors.CONVERSATION_HEADER_ID if lang_element == 'id' else Selectors.CONVERSATION_HEADER

            logger.info(f'Trying to check conversation header')
            print(f'----| Trying to check conversation header')
            browser.find_element(By.CSS_SELECTOR, conv_header)
        except NoSuchElementException as e:
            is_success = False
            logger.error(f'No such element conversation header, please check CSS Selector WhatsApp web. Error: {e}')
            logger.error(traceback.format_exc())
            print('----| No such element conversation header, please check CSS Selector WhatsApp web')
            logger.info('Trying to stop the program')
            print('----| Trying to stop the program')

            event.set()
            sys.exit(1)
        except Exception as e:
            is_success = False
            logger.error(f'Error when trying to check conversation header. Error: {e}')
            logger.error(traceback.format_exc())
            print(f'----| Error when trying to check conversation header')
            logger.info('Trying to stop the program')
            print('----| Trying to stop the program')

            event.set()
            sys.exit(1)

        if not is_success:
            try:
                WebDriverWait(browser, 120).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.POPUP))
                )
                # browser.find_element(By.CSS_SELECTOR, Selectors.POPUP_CONFIRM).click()
            except NoSuchElementException:
                is_success = True
                popup_not_found_msg = 'Error no such element popup invalid phone number, please check CSS Selector WhatsApp web.'
                print(popup_not_found_msg)
                logger.error(popup_not_found_msg)
                logger.error(traceback.format_exc())

                logger.info('Trying to stop the program')
                print('----| Trying to stop the program')
                event.set()
                sys.exit(1)
            except TimeoutException:
                is_success = True
                timeout_dialoge_msg = f'Timeout when program trying to find popup invalid phone number.'
                print(timeout_dialoge_msg)
                logger.error(timeout_dialoge_msg)
                logger.error(traceback.format_exc())

                logger.info('Trying to stop the program')
                print('----| Trying to stop the program')
                event.set()
                sys.exit(1)

            del is_success
            # skip current iteration when timeout
            continue
        else:
            try:
                # find text input box
                logger.info(f'Trying to find text input box')
                print(f'----| Trying to find text input box')
                input_box = WebDriverWait(browser, 120).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
                )
                logger.info(f'Trying write message to text input box')
                print(f'----| Trying write message to text input box')
                for line in message.splitlines():
                    stoppage_line = random.randint(10, 20)
                    logger.info(f'Dialogue Pause every {stoppage_line}')
                    for idx, word in enumerate(line):
                        if ((idx+1) % stoppage_line) == 0:
                            time.sleep(random.randint(5, 10))
                        input_box.send_keys(word)
                        time.sleep(.3)
                    #input_box.send_keys(line)
                    time.sleep(1)
                    input_box.send_keys(Keys.SHIFT, Keys.ENTER)

                time.sleep(9)

                # send message by press Enter
                logger.info('Send message by press Enter')
                print(f'----| Send message by press Enter')
                input_box.send_keys(Keys.ENTER)
                report_time_stop = tools.get_datetime('%H:%M:%S')

                # write temp count message limit
                message_limit = message_limit + 1
                tmp_message_limit = open('log/tmp_message_limit.txt', 'w')
                tmp_message_limit.write(str(message_limit))
                tmp_message_limit.close
                del tmp_message_limit

                # write temp soceng send
                tmp_soceng_send_file = open(f'log/tmp_{chat_type}_send.txt', 'a')
                tmp_soceng_send_file.write(f"{phone}|{message}\n")
                tmp_soceng_send_file.close
                del tmp_soceng_send_file

                time.sleep(5)

                # re-locate the input_box before interacting with it
                input_box = WebDriverWait(browser, 120).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, Selectors.MESSAGE_BOX))
                )
                input_box.send_keys(Keys.ESCAPE)
            except Exception as e:
                failed_sending_msg = f'Failed to {chat_type} with {phone_number}'
                print(failed_sending_msg)
                logger.error(failed_sending_msg + f' Error: {e}')
                report_time_stop = tools.get_datetime('%H:%M:%S')

                # write failed send message phone number to txt file
                failed_number = f'./report/{chat_type}/failed/failed_{chat_type}_{current_date}.txt'
                report_file_folder = Folder.is_exists(failed_number)
                if not report_file_folder:
                    logger.info(f'Create folder for failed report {chat_type}')
                    print(f'----| Create folder for failed report {chat_type}')
                    Folder.mkdir(failed_number)

                report_file = open(failed_number, 'a')  # append mode
                report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Error | {failed_sending_msg} | {message}\n')
                report_file.close()
                logger.info(f'Write failed send message phone number to txt file')
                print(f'----| Write failed send message phone number to txt file')

                # skip current iteration
                # continue

                logger.error(traceback.format_exc())
                # stop the program when failed to send message
                logger.info('Trying to stop the program')
                print('----| Trying to stop the program')
                event.set()
                sys.exit(1)

        if is_success or not event.is_set():
            success_sending_msg = f'Successfully {chat_type} chat with {phone_number}'
            print(f'----| {success_sending_msg}')
            logger.info(success_sending_msg)
            logger.info(f'Message {chat_type}: {message}.')
            print(f'Message {chat_type}: \n{message}.\n')

            # write success dialogue chat to txt file
            success_number = f'./report/{chat_type}/send/success_send_{current_date}.txt'
            report_file_folder = Folder.is_exists(success_number)
            if not report_file_folder:
                logger.info(f'Create folder for success report {chat_type}')
                print(f'----| Create folder for success report {chat_type}')
                Folder.mkdir(success_number)

            report_file = open(success_number, 'a')  # append mode
            report_file.write(f'{data_report} | {report_time_start} | {report_time_stop} | {HOST_NAME} - {IP_ADDRESS} | {phone} | Success | {success_sending_msg} | {message}\n')
            report_file.close()
            logger.info(f'Write success send message phone number to txt file')
            print(f'----| Write success send message phone number to txt file')
            del success_number, success_sending_msg, report_file

        # measure dialogue time
        time_end = time.perf_counter() - time_start
        print(f'----| It takes {time_end:.2f}s for {chat_type} with {phone_number}')
        del time_start, time_end, is_success, phone_number, phone, handles, data_report, report_time_start, report_time_stop, msg_limit

        random_number = random.randint(start_interval, end_interval)
        logger.info(f'Rest in {random_number}s')
        print(f'\r----| Rest in {random_number}s\n')
        print('')
        time.sleep(random_number)
        del random_number

    print(f'\nProcessing {chat_type} is done\n')
    logger.info(f'Processing {chat_type} is done')
    time.sleep(5)

def sync_report():
    CONFIG_REPORT = os.getenv('UPLOAD_TO_SERVER', True)
    if CONFIG_REPORT:
        print('\nUpload report to server')
        logger.info('Upload report to server')
        # upload report to server
        file_path = os.path.normpath(os.path.join(os.getcwd(), 'upload_file_report.sh'))
        os.chmod(file_path, os.stat(file_path).st_mode | 0o111)
        subprocess.run([file_path], shell=True)

        print('Successfully upload report to server\n')
        logger.info('Successfully upload report to server')
