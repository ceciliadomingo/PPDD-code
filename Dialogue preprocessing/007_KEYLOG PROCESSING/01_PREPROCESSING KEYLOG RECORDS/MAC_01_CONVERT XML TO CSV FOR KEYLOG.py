import pandas as pd
import xml.etree.ElementTree as ET

def extract_data_from_cells(row_element):
    cell_elements = row_element.findall('.//s:Cell', namespaces={"s": "urn:schemas-microsoft-com:office:spreadsheet"})
    row_data = [cell.find('.//s:Data', namespaces={"s": "urn:schemas-microsoft-com:office:spreadsheet"}).text for cell in cell_elements]
    return row_data

def convert_xml_to_csv(xml_file, csv_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    rows_data = []

    for worksheet in root.findall('.//s:Worksheet', namespaces={"s": "urn:schemas-microsoft-com:office:spreadsheet"}):
        for table in worksheet.findall('.//s:Table', namespaces={"s": "urn:schemas-microsoft-com:office:spreadsheet"}):
            for row in table.findall('.//s:Row', namespaces={"s": "urn:schemas-microsoft-com:office:spreadsheet"}):
                row_data = extract_data_from_cells(row)
                rows_data.append(row_data)

    columns=['Time', 'Action', 'Key', 'Modifier', 'MouseClick', 'x', 'y', 'Task']
    df = pd.DataFrame(rows_data, columns=columns)
    # Save the DataFrame to a CSV file
    df.to_csv(csv_file, index=False)



if __name__ == "__main__":
    xml_file_path = 'path/to/your/xml_file.xml'
    csv_file_path = 'path/to/your/csv_file.csv'
    convert_xml_to_csv(xml_file_path, csv_file_path)
