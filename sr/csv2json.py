import csv, sys, os, pandas, argparse, pydicom
from decimal import *

def getCTSourceSeriesUID(subjectDir):
  ctDir = os.path.join(subjectDir,"UnknownStudy", "CT")
  ctFile = os.listdir(ctDir)[0]
  dcm = pydicom.read_file(os.path.join(ctDir,ctFile))
  return dcm.SeriesInstanceUID

def getSEGInstanceUID(subjectDir):
  segDir = os.path.join(subjectDir,"UnknownStudy", "SEG")
  segFile = os.listdir(segDir)[0]
  dcm = pydicom.read_file(os.path.join(segDir,segFile))
  return dcm.SOPInstanceUID

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
    return {"CodeValue": self.codeValue, "CodeMeaning": self.codeMeaning, "CodingSchemeDesignator": self.codingSchemeDesignator}

class Metadata:

  m = {}

  def __init__(self):

    self.m["@schema"] = "https://raw.githubusercontent.com/qiicr/dcmqi/master/doc/schemas/sr-tid1500-schema.json#"
    self.m["SeriesDescription"] = "Radiomics features"

    self.m["Measurements"] = []

    self.measurementsGroup = {}
    self.measurementsGroup["measurementItems"] = []
    self.measurementsGroup["ReferencedSegment"] = 1
    self.m["Measurements"].append(self.measurementsGroup)


  def addMeasurement(self,value,quantityCode,unitsCode=CodedValue("1","UCUM","no units")):


    (pre,featureClass,name) = quantityCode.split('_')
    measurement = {}

    measurement["value"] = '%E' % Decimal(value)
    measurement["quantity"] = CodedValue(name).getDict()
    measurement["units"] = unitsCode.getDict()

    print(str(measurement))

    logTransformation = { "modifier": CodedValue("filter", "99RADIOMICSIO", "Image filter transformation").getDict(), \
                          "modifierValue": CodedValue("LoG", "99RADIOMICSIO", "Laplacian of Gaussian").getDict()}
    waveletTransformation = { "modifier": CodedValue("filter", "99RADIOMICSIO", "Image filter transformation").getDict(), \
                          "modifierValue": CodedValue("wavelet", "99RADIOMICSIO", "Wavelet transformation").getDict()}

    logParameter = { "derivationParameter": CodedValue("sigma", "99RADIOMICSIO", "Kernel size").getDict()}
    waveletSubband = { "modifier": CodedValue("wsubband", "99RADIOMICSIO", "Wavelet subband").getDict(), \
                          "modifierValue": CodedValue("", "99RADIOMICSIO", "").getDict()}

    # parse preprocessing parameters
    if pre.startswith("log"):
      print(pre)
      measurement["measurementModifiers"] = [logTransformation]
      measurement["measurementDerivationParameters"] = [logParameter]
      measurement["measurementDerivationParameters"][0]["derivationParameterValue"] = pre.split("-")[2]
      measurement["measurementDerivationParameters"][0]["derivationParameterUnits"] = CodedValue("1","UCUM","no units").getDict()

    if pre.startswith("wavelet"):
      measurement["measurementModifiers"] = [waveletTransformation, waveletSubband]
      measurement["measurementModifiers"][1]["modifierValue"]["CodeValue"] = pre.split("-")[1]
      measurement["measurementModifiers"][1]["modifierValue"]["CodeMeaning"] = pre.split("-")[1]
      #measurement["measurementDerivationParameters"] = [waveletSubband]
      #measurement["measurementDerivationParameters"][0]["derivationParameterValue"] = "1" # parameter has to be a scalar! pre.split("-")[1]
      #measurement["measurementDerivationParameters"][0]["derivationParameterUnits"] = CodedValue("1","UCUM","no units").getDict()

    measurementItems = self.m["Measurements"][0]["measurementItems"]
    self.m["Measurements"][0]["measurementItems"].append(measurement)

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
    print("Found duplicate column names in the input file:"+duplicates)
    return False
  return True

def main():

  '''
  parser = argparse.ArgumentParser(usage="--csv <input CSV file> --subject <subject ID> --json <output JSON file> --dicomSeries <directory with DICOM files> --dicomSEG <DICOM segmentation>")
  parser.add_argument("--csv", help="CSV file produced by pyradiomics", type=str)
  parser.add_argument("--subject", help="ID of the subject to store measurements for", type=str)
  parser.add_argument("--json", help="Name of the output JSON file", type=str)
  #parser.add_argument("dicomSeries",metavar="dicomImagesDir",help="Directory with the DICOM files")
  '''

  parser = argparse.ArgumentParser(usage="-- input <folder> --output <folder> --csv <path>, where input folder is the directory for a single subject")
  parser.add_argument("--input", help="Input folder", type=str)
  parser.add_argument("--output", help="Output folder", type=str)
  parser.add_argument("--csv", help="Input CSV file", type=str)

  args = parser.parse_args()

  inputCSV = args.csv
  subjectID = os.path.split(args.input)[-1]
  outputJSON = os.path.join(args.output,subjectID+"_features.json")

  columnNamesUnique(inputCSV)

  df = pandas.read_csv(inputCSV, index_col=0)
  print(df.columns)

  d = df.transpose().to_dict(orient='series')
  if not subjectID in d.keys():
    print("Failed to find the info for the subject "+subjectID+" requested")
    return

  m = Metadata()

  subjectItems = d[subjectID]
  #print subjectItems.keys()

  featurePrefixes = set()
  for featureName,featureValue in subjectItems.iteritems():
    featureNameSplit = featureName.split('_')
    if len(featureNameSplit)<3 or featureNameSplit[0] == "general":
      continue
    m.addMeasurement(featureValue, featureName)
    featurePrefixes.add(featureName.split('_')[0])

  print(featurePrefixes)
    #m.m[featureName] = d[subjectID][featureName]

  # get metadata for the referenced segmentation
  ctSeriesUID = getCTSourceSeriesUID(args.input)
  segInstanceUID = getSEGInstanceUID(args.input)

  print(ctSeriesUID+" "+segInstanceUID)

  m.m["Measurements"][0]["SourceSeriesForImageSegmentation"] = ctSeriesUID
  m.m["Measurements"][0]["segmentationSOPInstanceUID"] = segInstanceUID
  m.m["Measurements"][0]["TrackingIdentifier"] = "Nodule1"

  m.m["Measurements"][0]["Finding"] = {  "CodeValue": "M-03010", "CodingSchemeDesignator": "SRT", "CodeMeaning": "Nodule"}
  m.m["Measurements"][0]["FindingSite"] = {"CodeValue": "T-28000", "CodingSchemeDesignator": "SRT", "CodeMeaning": "Lung"}

  m.m["observerContext"] = {}
  m.m["observerContext"]["ObserverType"] = "PERSON"
  m.m["observerContext"]["PersonObserverName"] = "Reader1"
  m.m["compositeContext"] = os.listdir(os.path.join(args.input,"UnknownStudy","SEG"))

  m.saveToFile(outputJSON)

if __name__ == '__main__':
  main()
