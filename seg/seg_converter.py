import sys, os, argparse, tempfile, shutil, itk, glob, json, copy
import SimpleITK as sitk
from subprocess import call

'''
class LIDCSEGConverter:
  int __init__(self):
    self.tempDir = 
'''
# from https://itk.org/Doxygen/html/itkSpatialOrientation_8h_source.html
# these are missing in itk-python
ITK_COORDINATE_UNKNOWN = 0
ITK_COORDINATE_Right = 2
ITK_COORDINATE_Left = 3
ITK_COORDINATE_Posterior = 4
ITK_COORDINATE_Anterior = 5
ITK_COORDINATE_Inferior = 8
ITK_COORDINATE_Superior = 9 

ITK_COORDINATE_PrimaryMinor = 0
ITK_COORDINATE_SecondaryMinor = 8
ITK_COORDINATE_TertiaryMinor = 16

ITK_COORDINATE_ORIENTATION_RAS = ( ITK_COORDINATE_Right \
                                      << ITK_COORDINATE_PrimaryMinor ) \
                                    + ( ITK_COORDINATE_Anterior << ITK_COORDINATE_SecondaryMinor ) \
                                    + ( ITK_COORDINATE_Superior << ITK_COORDINATE_TertiaryMinor )

ITK_COORDINATE_ORIENTATION_LPS = ( ITK_COORDINATE_Left \
                                      << ITK_COORDINATE_PrimaryMinor ) \
                                    + ( ITK_COORDINATE_Posterior << ITK_COORDINATE_SecondaryMinor ) \
                                    + ( ITK_COORDINATE_Superior << ITK_COORDINATE_TertiaryMinor )

ITK_COORDINATE_ORIENTATION_LSP = ( ITK_COORDINATE_Left \
                                      << ITK_COORDINATE_PrimaryMinor ) \
                                    + ( ITK_COORDINATE_Superior << ITK_COORDINATE_SecondaryMinor ) \
                                    + ( ITK_COORDINATE_Posterior << ITK_COORDINATE_TertiaryMinor )


ITK_COORDINATE_ORIENTATION_RSP = ( ITK_COORDINATE_Right \
                                              << ITK_COORDINATE_PrimaryMinor ) \
                                              + ( ITK_COORDINATE_Superior << ITK_COORDINATE_SecondaryMinor ) \
                                           + ( ITK_COORDINATE_Posterior << ITK_COORDINATE_TertiaryMinor )

ITK_COORDINATE_ORIENTATION_RSA = ( ITK_COORDINATE_Right \
                                               << ITK_COORDINATE_PrimaryMinor ) \
                                        + ( ITK_COORDINATE_Superior << ITK_COORDINATE_SecondaryMinor ) \
                                           + ( ITK_COORDINATE_Anterior << ITK_COORDINATE_TertiaryMinor )
def reconstructCTVolume(srcDir, destFile):
  tempDir = tempfile.mkdtemp()
  call(['dicom2nifti', srcDir, tempDir])
  print 'dicom2nifti completed'
  outputFiles = os.listdir(tempDir)
  if not len(outputFiles):
    return False
  tempFile = os.path.join(tempDir, outputFiles[0])
  try:
    sitk.ReadImage(tempFile)
  except:
      return False
  try:
    # reorient
    ImageType = itk.Image[itk.SS, 3]
    reader = itk.ImageFileReader[ImageType].New()
    reader.SetFileName(tempFile)
    reader.Update()

    image = reader.GetOutput()
    reorient = itk.OrientImageFilter[ImageType,ImageType].New()
    reorient.SetInput(image)
    reorient.SetDesiredCoordinateOrientation(ITK_COORDINATE_ORIENTATION_RSP)
    reorient.Update();
    reoriented = reorient.GetOutput()

    writer = itk.ImageFileWriter[ImageType].New()
    writer.SetInput(reoriented)
    writer.SetFileName(destFile)
    writer.Update()
    
    return True
  except:
    return False



  return True

def getSegmentationMeta(name):
  if name.find('manual')>=0:
    segType = "MANUAL"
  else:
    segType = "SEMIAUTOMATIC"

  readerId = name.split('_')[1]
  noduleId = name.split('_')[-1]

  return (readerId,noduleId,segType)

def saveDICOMSEG(segPath,imageSeriesPath,jsonFile,dicomSEGFile):
  call(['itkimage2segimage','--inputDICOMDirectory',imageSeriesPath,'--inputMetadata',jsonFile,'--inputImageList',segPath,'--outputDICOM',dicomSEGFile])

def fixupSegmentation(segIn, refImage, segOut):
  i=sitk.ReadImage(refImage)
  s=sitk.ReadImage(segIn)

  d=s.GetDirection()[:-1]+(-1.0,)
  o=i.GetOrigin()
  o=o[:-1]+(-10.,)

  s.SetDirection(d)
  s.SetOrigin(o)

  sitk.WriteImage(s, segOut, True)

def main():
  print 'Note: this tool is developed specifically for converting LIDC-IDRI and related datasets \ngenerated \
   as part of the work on the pyradiomics Cancer Research paper.\nThis is not a general purpose tool!'
  parser = argparse.ArgumentParser(prog=sys.argv[0])
  parser.add_argument('--DICOMroot', help='Root directory with the DICOM image files', type=str, default='/Users/fedorov/Dropbox-work/Dropbox (Partners HealthCare)/all_four_readers_approved/LIDC-IDRI')
  parser.add_argument('--ITKroot', help='Root directory with the segmentations saved in ITK format', type=str, default='/Users/fedorov/Dropbox-work/Dropbox (Partners HealthCare)/all_four_readers_approved/')
  parser.add_argument('--JSONmeta', help='JSON file with the metadata needed for dcmqi conversion', type=str, default='/Users/fedorov/github/LIDC-IDRI-conversion/seg/nodule_manual.json')
  parser.add_argument('--subjectID', help='Patient id as an integer. The actual patient ID will be formed as LIDC-IDRI-%04i', type=int)

  args = parser.parse_args()

  print args.subjectID
  # Reconstruct input CT series into a volume
  if args.subjectID:
    subjectFullID = 'LIDC-IDRI-%04i' % args.subjectID
    subjectsToProcess = [subjectFullID]
  else:
    # process all subjects for which we have DICOMs
    subjectsToProcess = [os.path.split(x)[-1] for x in glob.glob(os.path.join(args.DICOMroot,"LIDC-IDRI-????"))]

  print 'Processing subjects',subjectsToProcess

  meta = json.load(open(args.JSONmeta,'r'))

  for subjectFullID in subjectsToProcess:

    print "Processing",subjectFullID

    imageSeriesFolder = os.path.join(args.DICOMroot, subjectFullID)
    reconstructionsFolder = os.path.join(args.ITKroot, subjectFullID, 'UnknownStudy', 'Reconstructions')
    segmentationsFolder = os.path.join(args.ITKroot, subjectFullID, 'UnknownStudy', 'Segmentations')

    if not (os.path.exists(imageSeriesFolder) and \
        os.path.exists(reconstructionsFolder) and \
        os.path.exists(segmentationsFolder)):
      print 'ERROR: Some of the folders do not exist, skipping this subject'
      continue

    reconstructionDest = os.path.join(reconstructionsFolder, 'correct_origin.nrrd')
    if not reconstructCTVolume(imageSeriesFolder, reconstructionDest):
      print 'Failed to convert input volume!'
      return
  
    segmentations = glob.glob(os.path.join(segmentationsFolder,"read*nodule_?.nii.gz"))
    for seg in segmentations:

      segPrefix = seg.split('.')[0]
      (readerID,noduleID,segType) = getSegmentationMeta(os.path.split(segPrefix)[-1])


      print '  segmentation',segPrefix

      segmentationDest = os.path.join(segmentationsFolder, segPrefix+'_correct_origin.nrrd')

      # Fix image origin in the segmentation to be consistent with that in the CT
      # series
      segmentationPath = os.path.join(segmentationsFolder, seg)
      fixupSegmentation(segmentationPath, reconstructionDest, segmentationDest)

      # Run dcmqi converter for the updated segmentation image

      segMeta = copy.deepcopy(meta)
      description = "Nodule "+noduleID+" Reader "+readerID
      segMeta["segmentAttributes"][0][0]["SegmentDescription"] = "Nodule "+noduleID+" Reader "+readerID
      segMeta["segmentAttributes"][0][0]["SegmentAlgorithmType"] = segType
      if segType == "SEMIAUTOMATIC":
        segMeta["segmentAttributes"][0][0]["SegmentAlgorithmName"] = "3DSlicer"
        description = description+" semiauto"
      else:
        description = description+" manual"
      segMeta["ContentCreatorName"] = "Reader"+readerID
      segMeta["SeriesDescription"] = description

      dicomSEGFile = os.path.join(segmentationsFolder, segPrefix+'.dcm')
      dicomMetaFile = os.path.join(segmentationsFolder, segPrefix+'.json')
      with open(dicomMetaFile,'w') as jsonFile:
        json.dump(segMeta, jsonFile)

      saveDICOMSEG(str(segmentationDest),str(imageSeriesFolder),str(dicomMetaFile),str(dicomSEGFile))      
      print 'Saved segmentation to',dicomSEGFile

if __name__ == '__main__':
  main()
