import csv, sys, os, pandas, argparse

class CodedValue:
  def __init__(self,codeValue):
    self.codeValue = codeValue
    self.codingSchemeDesignator = "99RADIOMICSIO"
    self.codeMeaning = codeValue

class Metadata:

  m = {}

  def __init__(self):

    self.m["@schema"] = "https://raw.githubusercontent.com/qiicr/dcmqi/master/doc/schemas/sr-tid1500-schema.json#"
    self.m["SeriesDescription"] = "Radiomics features"

    self.m["Measurements"] = {}
    self.m["Measurements"]["measurementItems"] = {}
    self.m["ReferencedSegment"] = 1

  def addMeasurement(self,code):


  def saveToFile(self,fileName):
    import json
    with open(fileName,'w') as f:
      json.dump(self.m,f,indent=2)

def main():

  parser = argparse.ArgumentParser(usage="--csv <input CSV file> --subject <subject ID> --json <output JSON file> --dicomSeries <directory with DICOM files> --dicomSEG <DICOM segmentation>")
  parser.add_argument("csv",metavar="inputCSV", help="CSV file produced by pyradiomics")
  parser.add_argument("subject",metavar="subjectID",help="ID of the subject to store measurements for")
  parser.add_argument("json",metavar="outputJSON",help="Name of the output JSON file")
  parser.add_argument("dicomSeries",metavar="dicomImagesDir",help="Directory with the DICOM files
      
    return

  inputCSV = sys.argv[1]
  subjectID = sys.argv[2]
  outputJSON = sys.argv[3]

  df = pandas.read_csv(inputCSV, index_col=0)
  d = df.transpose().to_dict(orient='series')
  if not subjectID in d.keys():
    print "Failed to find the info for the subject",sys.argv[2],"requested"
    return

  m = Metadata()

  for featureName in d[subjectID].keys():
    m.m[featureName] = d[subjectID][featureName]

  m.saveToFile(outputJSON)

if __name__ == '__main__':
  main()
