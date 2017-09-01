import csv, sys, os, pandas, argparse

class CodedValue:
  def __init__(self,codeValue):
    self.codeValue = codeValue
    self.codingSchemeDesignator = "99RADIOMICSIO"
    self.codeMeaning = codeValue

  def __init__(self,value,scheme="99RADIOMICSIO",meaning=None):
    self.codeValue = value
    self.codingSchemeDesignator = scheme
    if meaning is None:
      self.codeMeaning = value
    else:
      self.codeMeaning = meaning

  def getDict(self):
    return {"CodeValue": self.codeValue, "CodeMeaning": self.codeMeaning, "codingSchemeDesignator": self.codingSchemeDesignator}

class Metadata:

  m = {}

  def __init__(self):

    self.m["@schema"] = "https://raw.githubusercontent.com/qiicr/dcmqi/master/doc/schemas/sr-tid1500-schema.json#"
    self.m["SeriesDescription"] = "Radiomics features"

    self.m["Measurements"] = {}
    self.m["Measurements"]["measurementItems"] = []
    self.m["ReferencedSegment"] = 1

  def addMeasurement(self,value,quantityCode,unitsCode=CodedValue("1","UCUM","no units")):
    measurement = {}
    measurement["value"] = value
    measurement["quantity"] = quantityCode.getDict()
    measurement["units"] = unitsCode.getDict()
    self.m["Measurements"]["measurementItems"].append(measurement)
    return

  def saveToFile(self,fileName):
    import json
    with open(fileName,'w') as f:
      json.dump(self.m,f,indent=2, sort_keys=True)

def columnNamesUnique(fileName):
  with open(fileName,'r') as f:
    names = f.readline()
  names = names.split(',')
  from collections import Counter
  duplicates = [k for k,v in Counter(names).items() if v>1]
  if len(duplicates):
    print "Found duplicate column names in the input file:", duplicates
    return False
  return True

def main():

  parser = argparse.ArgumentParser(usage="--csv <input CSV file> --subject <subject ID> --json <output JSON file> --dicomSeries <directory with DICOM files> --dicomSEG <DICOM segmentation>")
  parser.add_argument("--csv", help="CSV file produced by pyradiomics", type=str)
  parser.add_argument("--subject", help="ID of the subject to store measurements for", type=str)
  parser.add_argument("--json", help="Name of the output JSON file", type=str)
  #parser.add_argument("dicomSeries",metavar="dicomImagesDir",help="Directory with the DICOM files")

  args = parser.parse_args()

  inputCSV = args.csv
  subjectID = args.subject
  outputJSON = args.json

  columnNamesUnique(inputCSV)

  df = pandas.read_csv(inputCSV, index_col=0)
  d = df.transpose().to_dict(orient='series')
  if not subjectID in d.keys():
    print "Failed to find the info for the subject",sys.argv[2],"requested"
    return

  m = Metadata()

  subjectItems = d[subjectID]
  #print subjectItems.keys()

  for featureName,featureValue in subjectItems.iteritems():
    featureNameSplit = featureName.split('_')
    if len(featureNameSplit)<3 or featureNameSplit[0] == "general":
      continue
    m.addMeasurement(featureValue, CodedValue(featureName))
    #m.m[featureName] = d[subjectID][featureName]

  m.saveToFile(outputJSON)

if __name__ == '__main__':
  main()
