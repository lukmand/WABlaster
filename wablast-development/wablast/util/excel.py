import pandas as pd
import openpyxl as xl

from os import path
from .tools import Folder

def read_file(file):
    data = pd.read_excel(file)
    df = pd.DataFrame(data)

    # get column index in phone list
    column = map(str, df.columns)
    data_list = list(column)
    df2 = pd.DataFrame([data_list], columns=[i for i in df])

    # insert column index name in phone number file to new array phone list
    phone_list = pd.concat([df2, df], ignore_index=True)

    data = None
    df = None
    column = None
    df2 = None

    # return array phone list number
    return phone_list

def write_file(array, filename):
    file_path = path.expanduser(filename)
    # create a pandas dataframe from data array
    df = pd.DataFrame(array)

    # create a pandas excel writer
    writer = pd.ExcelWriter(file_path, mode='a')

    # convert the dataframe to an Excel object
    df.to_excel(writer, sheet_name='Sheet1', index=False, header=False)

    # close the pandas excel writer and output the excel file
    writer.close()

    df = None
    del file_path

def append_data(data, file, start_row: int = 0):
    df = pd.DataFrame([data])
    df.columns = ['Date', 'Start', 'End', 'Phone', 'Status', 'Response Status', 'Text Message']
    folder = Folder()

    file_path = path.expanduser(file)
    is_exists = folder.is_exists(file_path)
    if not is_exists:
        # create directory if not exist
        folder.mkdir(file_path)

        # create file excel
        with pd.ExcelWriter(file_path) as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False, header=True)
    else:
        # update file excel
        with pd.ExcelWriter(file_path, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False, header=False, startrow=start_row)

    df = None
    folder = None
    del file_path, is_exists

def count_row(file):
    folder = Folder()
    file_path = path.expanduser(file)
    is_exists = folder.is_exists(file_path)
    if not is_exists:
        folder = None
        del file_path, is_exists
        return 0
    else:
        files = xl.load_workbook(file_path, enumerate)
        sheet = files['Sheet1']
        rows = sheet.max_row
        files.close()

        folder = None
        sheet = None
        del file_path, is_exists
        return rows
