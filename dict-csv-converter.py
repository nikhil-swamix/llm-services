"""
Objective:
name,alpha-2,alpha-3,country-code,iso_3166-2,region,sub-region,intermediate-region,region-code,sub-region-code,intermediate-region-code
Afghanistan,AF,AFG,004,ISO 3166-2:AF,Asia,Southern Asia,"",142,034,""
Åland Islands,AX,ALA,248,ISO 3166-2:AX,Europe,Northern Europe,"",150,154,""
Albania,AL,ALB,008,ISO 3166-2:AL,Europe,Southern Europe,"",150,039,""

-----
to conver this to a dictionary format where only "xx":"name" are there

"""

import csv, json

data_csv_file = "../data/country-db.csv"


def convert_csv_to_dict(csv_file_path):
    country_dict = {}
    with open(csv_file_path, mode="r", encoding="utf-8") as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            country_dict[row["alpha-2"]] = row["name"]
    return country_dict


if __name__ == "__main__":
    country_dict = convert_csv_to_dict(data_csv_file)

    # save to json
    with open("../data/country-db.json", "w", encoding="utf-8") as json_file:
        json.dump(country_dict, json_file, ensure_ascii=False, indent=4)
    print("Conversion completed and saved to country-db.json")
