
from matplotlib import pyplot as plt
import csv

def main():
    f = open('data.csv', 'r')
    reader = csv.reader(f)
    data = []
    for i, row in enumerate(reader):
        data.append(float(row[0]))

    plt.plot(data)
    plt.show()


if __name__ == "__main__":
    main()
