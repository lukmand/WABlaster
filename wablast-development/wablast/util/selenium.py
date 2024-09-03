from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

def find_element_if_exists(driver: WebDriver | WebElement, *args, **kargs) -> WebElement:
    try:
        return driver.find_element(*args, **kargs)
    except NoSuchElementException:
        return None

def element_exists(driver: WebDriver | WebElement, *args, **kargs) -> bool:
    return find_element_if_exists(driver, *args, **kargs) is not None

def paste_text(driver, element, content):
    escaped_content = content.replace("`", "\\`")
    driver.execute_script(
    f'''
const text = `{escaped_content}`;
const dataTransfer = new DataTransfer();
dataTransfer.setData('text', text);
const event = new ClipboardEvent('paste', {{
  clipboardData: dataTransfer,
  bubbles: true
}});
arguments[0].dispatchEvent(event)
''',
    element)