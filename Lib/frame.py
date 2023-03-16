import time
import threading
import PySimpleGUI as sg

from serial.serialutil import SerialException
from chamber import _TempKeywords
from utils import Utils


THREAD_EVENT = '-THREAD-'


def get_temp(stopEvent, window):
    temp_box = _TempKeywords()
    while True:
        if stopEvent.is_set():
            break
        time.sleep(0.2)
        window.write_event_value(key='-THREAD-', value=temp_box.get_current_temperature())


def run():
    layout = [
        [sg.VPush()],
        [sg.Push(), sg.Text('设置温度:', font='楷体 14'), sg.Input(size=(10, 2), key='-INPUT-'), sg.Text('℃', font='楷体 14'), sg.Push()],
        [sg.Text('')],
        [sg.Push(), sg.Text('当前温度:', key='-READ-', font='楷体 14'), sg.Text('', text_color='red', size=(7, 1), key='-DISPLAY-', font='楷体 14'), sg.Text('℃', font='楷体 14'), sg.Push()],
        [sg.Text('')],
        [sg.Push(), sg.Button('设置', size=(10, 2), font='楷体 14'), sg.Push(), sg.Button('停止', size=(10, 2), font='楷体 14'), sg.Push(), sg.Button('退出', size=(10, 2), font='楷体 14'), sg.Push()],
        [sg.VPush()],
        [sg.Push(), sg.Text('@Copyright Wistron NeWeb Corp.', font='楷体 12'), sg.Push()]
    ]

    window = sg.Window('TEMI1000 Tool', layout, auto_size_text=True, size=(600, 300))
    temp_box = _TempKeywords()
    stop_event = threading.Event()
    isPopup = False
    initTemp = 1000

    while True:
        event, values = window.read()
        targetTemp = values['-INPUT-']

        if targetTemp is not None:
            if targetTemp != initTemp:
                initTemp = targetTemp
                isPopup = False

        if event in (sg.WINDOW_CLOSED, '退出'):
            break

        if event == '设置':
            stop_event.clear()

            try:
                if not targetTemp:
                    raise ValueError
                else:
                    temp = round(float(targetTemp), 1)
                if temp <= -70 or temp >= 150:
                    raise ValueError
            except ValueError:
                sg.PopupError('请检查输入的温度是否正确！', font='楷体 13')
                continue

            try:
                temp_box.set_temperature_output(temp)
                temp_box.activate_output()
            except SerialException:
                sg.PopupError('未找到可用端口，请检查端口连接！', font='楷体 13')
                continue

            threading.Thread(target=get_temp, args=(stop_event, window,), daemon=True).start()

        if event == '停止':
            stop_event.set()
            time.sleep(0.5)
            try:
                temp_box.deactivate_output()
            except SerialException:
                sg.PopupError('未找到可用端口，请检查端口连接！', font='楷体 13')
                continue

        if event == THREAD_EVENT:
            window['-DISPLAY-'].update(values[event])

            if Utils.floatEquals(values[event], round(float(targetTemp), 1), uncertainty=0.2):
                if not isPopup:
                    sg.Popup('温度设定完成！', font='楷体 13')
                isPopup = True
                continue

    window.close()


if __name__ == '__main__':
    run()