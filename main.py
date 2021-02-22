import requests
from bs4 import BeautifulSoup
import re
from os import mkdir, listdir
import openpyxl
# from selenium import webdriver


def get_page_count(site, category):
    # Данная функция ищет пагинатор на странице и вытаскивает из него количество страниц
    r = requests.get("https://{}/{}/?page=1".format(site, category))
    page_count = 0
    # Создаем папку согласно категории
    mkdir('tmp/categories/{}/'.format(category))
    with open('tmp/categories/{}/page1.html'.format(category), 'a') as first_page:
        first_page.write(r.text)
    with open('tmp/categories/{}/page1.html'.format(category), 'r') as first_page:
        soup = BeautifulSoup(first_page.read(), 'html.parser')
        paginator = soup.find_all('div', {'class': 'row paginator'})
        page_count_string = paginator[0].contents[3].contents[0]
        count_in_text = re.search('всего (.+?) страниц', page_count_string)
        if count_in_text:
            page_count = int(count_in_text.group(1))
    return page_count


def download():
    site = 'stomshop.pro'
    # Забираем категории из файла(их немного, проще руками заполнить файл)
    # В нашем случае url = "https://stomshop.pro/category_name/"
    with open('categories.txt', 'r') as cats:
        categories = [line[:-1] for line in cats.readlines()]
    # print(categories)
    for category in categories:
        page_count = get_page_count(site, category)
        print("Next category {}. {} pages.".format(category, page_count))
        if page_count:
            while page_count > 1:
                r = requests.get("https://{}/{}/?page={}".format(site, category, page_count))
                with open('tmp/categories/{}/page{}.html'.format(category, page_count), 'a') as page:
                    page.write(r.text)
                print("Page {} in category {} is ready.".format(page_count, category))
                page_count -= 1
                print("Next page: {}".format(page_count))
        # В каждой категории выгружаем все страницы, чтобы составить список товаров категории
        pass


def get_product_links(category):
    # Данная функция возвращает список ссылок на все продукты категории
    # Для ее работы списки товаров должны быть выгружены функцией download()
    product_links = []
    for file in listdir('tmp/categories/{}/'.format(category)):
        with open('tmp/categories/{}/{}'.format(category, file), 'r') as f:
            soup = BeautifulSoup(f, 'html.parser')
            links = soup.find_all('a', {'class': 'text-special'})
            part = [link.get('href') for link in links]
            product_links += part
    return product_links


def get_product_data(link):
    print('Fetching product data from: {}'.format(link))
    r = requests.get(link)
    file_name = link.split('/')[3]

    with open('tmp/products/{}'.format(file_name), 'a') as product:
        product.write(r.text)
    with open('tmp/products/{}'.format(file_name), 'r') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        breadcrumb = soup.find('ul', {'class': 'breadcrumb text-center'})
        category = breadcrumb.find_all('li')[1].span.contents[0]
        # Проверить наличие других
        subcategory = ''
        if len(breadcrumb.find_all('li'))>3:
            counter = len(breadcrumb.find_all('li')) - 2
            while counter > 1:
                subcategory += '{}, '.format(breadcrumb.find_all('li')[counter].span.contents[0])
                counter = counter - 1
        name = breadcrumb.find_all('li')[-1].contents[0]
        code = soup.find('div', {'class': 'h2'}).meta.attrs['content']
        if 'Артикул' in soup.find('div', {'class': 'h2'}).small.contents[0]:
            art = soup.find('div', {'class': 'h2'}).small.contents[0].split('Артикул: ')[1].split(')')[0]
            code += art
        in_stock = ''  # soup.find('p', {'class': 'h4-product'}).contents[0].split(':')[1][1:]
        delivery = ''  # soup.find('div', {'class': 'stock-7'}).div.contents[0]
        brand = ''  # soup.find_all('div', {'class': 'stock-7'})[1].h4.contents[0].split('Бренд: ')[1]
        lic = ''
        free_delivery = ''

        product_points = soup.find('div', {'class': 'product-points'}).find_all('div')
        for s in product_points:
            if 'Наличие: ' in s.text:
                in_stock = s.text.split('Наличие: ')[1].split("\n")[0]
                delivery = s.text.split("\n")[3]
            elif 'Бренд: ' in s.text:
                brand = s.text.split('Бренд: ')[1].split("\n")[0]
            elif 'Подходит для лицензирования' in s.text:
                lic = 'Подходит для лицензирования'

        if soup.find('div', {'class': 'product-delivery'}) is not None:
            free_delivery = soup.find('div', {'class': 'product-delivery'}).text.split("\n")[2]

        price_old = soup.find('span', {'class': 'price-old'}).text
        price_new = soup.find('span', {'class': 'price-1-new'}).text
        link_cheaper = ''
        if soup.find('a', {'class': 'link-cheaper'}) is not None:
            link_cheaper = soup.find('a', {'class': 'link-cheaper'}).text
        product_warranty = ''
        if soup.find('div', {'id': 'product-warranty-block'}) is not None:
            product_warranty = soup.find('div', {'id': 'product-warranty-block'}).text

        docs = ''
        if soup.find('div', {'id': 'tab-description'}).find_all('a', {"style": "text-decoration:none;"}) != []:
            for doc in soup.find('div', {'id': 'tab-description'}).find_all('a', {"style": "text-decoration:none;"}):
                doc_name = doc.get('href').split("/")[-1]

                docs += "{}, ".format(doc.get('href').split("/")[-1])
                r = requests.get('https://stomshop.pro/{}'.format(doc.get('href')))
                with open('tmp/files/docs/{}'.format(doc_name), 'wb') as doc_save:
                    doc_save.write(r.content)

        specs = soup.find('div', {'id': 'tab-specification'}).text
        desc = soup.find('div', {'id': 'tab-description'}).text

        reviews = ''
        if soup.find('div', {'id': 'review'}) is not None:
            reviews = soup.find('div', {'id': 'review'}).text
        qas = ''
        if soup.find('div', {'id': 'qa'}) is not None:
            qas = soup.find('div', {'id': 'qa'}).text

        stickers = ''
        if soup.find('div', {'class': 'xd_stickers_wrapper xd_stickers_product'}) is not None:
            for sticker in soup.find('div', {'class': 'xd_stickers_wrapper xd_stickers_product'}).find_all('div'):
                stickers += '{}, '.format(sticker.text.split("\t")[8])

        # files = ''
        # reg_docs = ''
        # chromeOptions = webdriver.ChromeOptions()
        # prefs = {"download.default_directory": "tmp/files/reg_docs/"}
        # chromeOptions.add_experimental_option("prefs", prefs)
        # chromeOptions.add_argument("--kiosk")
        #
        # driver = webdriver.Chrome(chrome_options=chromeOptions)
        # driver.get(link)
        # elem = driver.find_element_by_partial_link_text('Регистрационные документы')
        # elem.click()
        # elems = driver.find_elements_by_name('email')
        # for el in elems:
        #     el.find_elements_by_name('email')
        #
        #     el.send_keys('1@1.ru')
        # links = driver.find_elements_by_class_name('doc-lnk')
        # for el in links:
        #     el.click()
        # driver.close()
        data = {
            'Code': code,
            'Name': name,
            'URL': link,
            'Category': category,
            'Subcategory': subcategory,
            'In Stock': in_stock,
            'Delivery': delivery,
            'Brand': brand,
            'Licence': lic,
            'Free delivery': free_delivery,
            'Price old': price_old,
            'Price new': price_new,
            'Link cheaper': link_cheaper,
            'Warranty': product_warranty,
            'Specs': specs,
            'Description': desc,
            'Reviews': reviews,
            'Q&A(s)': qas,
            'Doc(s)': docs,
            'Registration docs': reg_docs
        }
    with open('tmp/products/{}.json'.format(file_name), 'a') as f:
        f.write(str(data))
    return data




def get_all_products_for_category(category, row):
    this_row = row
    for link in get_product_links(category):
        data = get_product_data(link)
        wb = openpyxl.load_workbook('output.xlsx')
        sheet = wb['DATA']
        for col in range(0, len(data)):
            cell = sheet.cell(row=this_row, column=col+1)
            cell.value = list(data.values())[col]

        wb.save('output.xlsx')
        print('Row {} added!'.format(this_row))
        this_row += 1
    return row


def get_site():
    row = 2

    pass


if __name__ == '__main__':
    pass

    get_all_products_for_category('nakonechniki-motory', 2)
    # print(get_product_links('nakonechniki-motory'))

    # print(get_product_data('https://stomshop.pro/vatech-ezray-portable'))
    # download()
    # print(get_page_count('stomshop.pro', 'stomatologicheskoye-oborudovaniye'))
