# -*- coding: utf-8 -*-
"""DLP_LAB3_310552054_林子恒.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1uplbdb9jZmy5kNm5xBOo1G8MBzOEdqRm
"""

!python -V
!nvcc --version
!nvidia-smi

#del resnet18

"""# Import library what I need"""

import os
import time
import shutil
import torch
import pandas as pd
import numpy as np
from PIL import Image
from tqdm.auto import tqdm
import torch.nn as nn
from torch.optim import SGD
from torch.utils.data import DataLoader
import torchvision.models as models
from torchvision.datasets import DatasetFolder
import torchvision.transforms as transforms
from sklearn.model_selection import KFold
from torch.utils.tensorboard import SummaryWriter
import seaborn as sns
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt

"""#Download the image data and unzip"""

!ls
if os.path.isfile("data.zip"):
  print("file is already exist")
else:
  print("file is not here")
  !gdown --id '1RTmrk7Qu9IBjQYLczaYKOvXaHWBS0o72' --output data.zip #download data.zip
if os.path.isdir("data"):
  print("file is already unzip")
else:
  print("unzip the file")
  !unzip -q data.zip

"""#mount the Google Drive"""

from google.colab import drive
drive.mount('/content/drive')
file_path = "drive/MyDrive/NYCU/109 Summer Deep Learning and Practice/assignment/[Lab3] Diabetic retinopathy detection/"

"""#Categorize the images and place the corresponding folders"""

train_img = pd.read_csv(file_path + 'train_img.csv')
train_label = pd.read_csv(file_path + 'train_label.csv')
test_img = pd.read_csv(file_path + 'test_img.csv')
test_label = pd.read_csv(file_path + 'test_label.csv')
train_set = (np.squeeze(train_img.values), np.squeeze(train_label.values))
test_set = (np.squeeze(test_img.values), np.squeeze(test_label.values))

if not os.path.isdir("data/training"):
  os.mkdir("data/training")
else:
  print("data/training "+"folder already have")

for i in range(5):
  if not os.path.isdir("data/training/0"+str(i)):
    os.mkdir("data/training/0"+str(i))
  else:
    print("data/training/0"+str(i)+" folder already have")

if not os.path.isdir("data/testing"):
  os.mkdir("data/testing")
else:
  print("data/testing "+"folder already have")

for i in range(5):
  if not os.path.isdir("data/testing/0"+str(i)):
    os.mkdir("data/testing/0"+str(i))
  else:
    print("data/testing/0"+str(i)+" folder already have")

if os.path.isfile("data/2576_right.jpeg"):
  shutil.move("data/2576_right.jpeg", "data/training/00")
if os.path.isfile("data/3798_left.jpeg"):
  shutil.move("data/3798_left.jpeg", "data/testing/00")

for i in range(len(train_set[0])):
  if os.path.isfile("data/"+str(train_set[0][i])+".jpeg"):
    shutil.move("data/"+str(train_set[0][i])+".jpeg", "data/training/0"+str(train_set[1][i]))

for i in range(len(test_set[0])):
  if os.path.isfile("data/"+str(test_set[0][i])+".jpeg"):
    shutil.move("data/"+str(test_set[0][i])+".jpeg", "data/testing/0"+str(test_set[1][i]))

tfm = transforms.Compose([
    transforms.Resize(224),
    transforms.ToTensor(),
    #transforms.Normalize(mean=[0.485, 0.456, 0.406],
     #                            std=[0.229, 0.224, 0.225])
])

tfm1 = transforms.Compose([
    transforms.Resize(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
])

train_set = DatasetFolder("data/training", loader=lambda x: Image.open(x), extensions="jpeg", transform=tfm)
test_set = DatasetFolder("data/testing", loader=lambda x: Image.open(x), extensions="jpeg", transform=tfm)
train_set1 = DatasetFolder("data/training", loader=lambda x: Image.open(x), extensions="jpeg", transform=tfm1)
test_set1 = DatasetFolder("data/testing", loader=lambda x: Image.open(x), extensions="jpeg", transform=tfm1)

transforms1 = torch.nn.Sequential(
  transforms.RandomHorizontalFlip(p=0),
  #transforms.RandomRotation(degrees=(0, 360))
)
scripted_transforms1 = torch.jit.script(transforms1)

transforms2 = torch.nn.Sequential(
  transforms.RandomHorizontalFlip(p=0.5),
  transforms.RandomRotation(degrees=(0, 360))
)
scripted_transforms2 = torch.jit.script(transforms2)

# Commented out IPython magic to ensure Python compatibility.
# %load_ext tensorboard
from tensorboard import notebook
notebook.list() # View open TensorBoard instances
# Control TensorBoard display. If no port is provided, 
# the most recently launched TensorBoard is used
'''notebook.display(port=6006, height=800)

notebook.display(port=6007, height=800)'''

# %tensorboard --logdir runs/

def set_DataLoader(train_set,test_set,batch_size = 32):
    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    test_loader = DataLoader(test_set, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    return train_loader , test_loader

def train(model,mode,n_epochs,train_loader,test_loader,test_loader2):
  count = 0
  writer = SummaryWriter()
  # "cuda" only when GPUs are available.
  device = "cuda" if torch.cuda.is_available() else "cpu"

  print("now device is",device)
  model = model.to(device)
  model.device = device
  #print(model)

  optimizer = torch.optim.Adam(model.parameters(), lr=0.0003, weight_decay=1e-5)
  # For the classification task, we use cross-entropy as the measurement of performance.
  criterion = nn.CrossEntropyLoss()

  for epoch in range(n_epochs):
      
      starttime = time.process_time()
    # ---------- Training ----------
      # Make sure the model is in train mode before training.
      model.train()
      
      # These are used to record information in training.
      train_loss = []
      train_accs = []
      # Iterate the training set by batches.
      if mode == 0:
        for batch in tqdm(train_loader):
            # A batch consists of image data and corresponding labels.
            imgs, labels = batch

            #''' Forward the data. (Make sure data and model are on the same device.)
            logits = model(scripted_transforms1(imgs.to(device)))
            # Calculate the cross-entropy loss.
            loss = criterion(logits, labels.to(device))

            # Gradients stored in the parameters in the previous step should be cleared out first.
            optimizer.zero_grad()

            # Compute the gradients for parameters.
            loss.backward()

            # Clip the gradient norms for stable training.
            grad_norm = nn.utils.clip_grad_norm_(model.parameters(), max_norm=10)

            # Update the parameters with computed gradients.
            optimizer.step()

            # Compute the accuracy for current batch.
            acc = (logits.argmax(dim=-1) == labels.to(device)).float().mean()

            # Record the loss and accuracy.
            train_loss.append(loss.item())
            train_accs.append(acc)
      else:
        if (count%2) == 0:
          for batch in tqdm(train_loader):
            # A batch consists of image data and corresponding labels.
            imgs, labels = batch

            #''' Forward the data. (Make sure data and model are on the same device.)
            logits = model(scripted_transforms1(imgs.to(device)))
            # Calculate the cross-entropy loss.
            loss = criterion(logits, labels.to(device))

            # Gradients stored in the parameters in the previous step should be cleared out first.
            optimizer.zero_grad()

            # Compute the gradients for parameters.
            loss.backward()

            # Clip the gradient norms for stable training.
            grad_norm = nn.utils.clip_grad_norm_(model.parameters(), max_norm=10)

            # Update the parameters with computed gradients.
            optimizer.step()

            # Compute the accuracy for current batch.
            acc = (logits.argmax(dim=-1) == labels.to(device)).float().mean()

            # Record the loss and accuracy.
            train_loss.append(loss.item())
            train_accs.append(acc)
        else:
          for batch in tqdm(test_loader2):
            # A batch consists of image data and corresponding labels.
            imgs, labels = batch

            #''' Forward the data. (Make sure data and model are on the same device.)
            logits = model(scripted_transforms2(imgs.to(device)))
            # Calculate the cross-entropy loss.
            loss = criterion(logits, labels.to(device))

            # Gradients stored in the parameters in the previous step should be cleared out first.
            optimizer.zero_grad()

            # Compute the gradients for parameters.
            loss.backward()

            # Clip the gradient norms for stable training.
            grad_norm = nn.utils.clip_grad_norm_(model.parameters(), max_norm=10)

            # Update the parameters with computed gradients.
            optimizer.step()

            # Compute the accuracy for current batch.
            acc = (logits.argmax(dim=-1) == labels.to(device)).float().mean()

            # Record the loss and accuracy.
            train_loss.append(loss.item())
            train_accs.append(acc)

            
      # The average loss and accuracy of the training set is the average of the recorded values.
      train_loss = sum(train_loss) / len(train_loss)
      train_acc = sum(train_accs) / len(train_accs)
      count += 1
      writer.add_scalar('Loss/train', train_loss, epoch)
      writer.add_scalar('Accuracy/train', train_acc, epoch)
      endtime = time.process_time()
      costtime = endtime - starttime
      # Print the information.
      print(f"[ Train | {epoch + 1:03d}/{n_epochs:03d} ] loss = {train_loss:.5f}, acc = {train_acc:.5f}, cost time = {costtime}")

    # ---------- Validation ----------
    # Make sure the model is in eval mode so that some modules like dropout are disabled and work normally.
    
      model.eval()
      starttime = time.process_time()
      # These are used to record information in validation.
      valid_loss = []
      valid_accs = []

      # Iterate the validation set by batches.
      for batch in tqdm(test_loader):
          # A batch consists of image data and corresponding labels.
          imgs, labels = batch

          # We don't need gradient in validation.
          # Using torch.no_grad() accelerates the forward process.
          with torch.no_grad():
            logits = model(imgs.to(device))

          # We can still compute the loss (but not the gradient).
          loss = criterion(logits, labels.to(device))

          # Compute the accuracy for current batch.
          acc = (logits.argmax(dim=-1) == labels.to(device)).float().mean()

          # Record the loss and accuracy.
          valid_loss.append(loss.item())
          valid_accs.append(acc)
      # The average loss and accuracy for entire validation set is the average of the recorded values.
      valid_loss = sum(valid_loss) / len(valid_loss)
      valid_acc = sum(valid_accs) / len(valid_accs)

      writer.add_scalar('Loss/valid', valid_loss, epoch)        
      writer.add_scalar('Accuracy/valid', valid_acc, epoch)
      endtime = time.process_time()
      costtime = endtime - starttime
      # Print the information.
      print(f"[ Valid | {epoch + 1:03d}/{n_epochs:03d} ] loss = {valid_loss:.5f}, acc = {valid_acc:.5f}, cost time = {costtime}")

  writer.close()

def predicte(model,test_loader):
  device = "cuda" if torch.cuda.is_available() else "cpu"
  model.eval()
  # Initialize a list to store the predictions.
  test_accs = []
  prediction_label = []
  groundtruth_label = []
  # Iterate the testing set by batches.
  for batch in tqdm(test_loader): # or in tqdm(test_loader):

      imgs, labels = batch
      groundtruth_label = groundtruth_label + labels.tolist()
      # Using torch.no_grad() accelerates the forward process.
      with torch.no_grad():
          logits = model(imgs.to(device))
          prediction_label = prediction_label + (logits.argmax(dim=-1)).tolist()
      # Compute the accuracy for current batch.
          acc = (logits.argmax(dim=-1) == labels.to(device)).float().mean()

          # Record the loss and accuracy.
          test_accs.append(acc)

  test_acc = sum(test_accs) / len(test_accs)
  print(test_acc)
  print(f"test_set acc = {test_acc:.5f}")
  return test_acc , prediction_label , groundtruth_label

def plot_confusion_matrix(groundtruth_label,prediction_label,normalize="all"): 
  sns.set()
  f,ax=plt.subplots()
  C2= confusion_matrix(groundtruth_label, prediction_label, labels=[0, 1, 2 ,3 ,4],normalize="all")
  sns.heatmap(C2,annot=True,ax=ax,cmap="YlGnBu")
  ax.set_title('confusion matrix')
  ax.set_xlabel('predict')
  ax.set_ylabel('true')

def save_model(model,model_name):
  FILE = file_path + str(model_name) + ".pth"
  torch.save(model.state_dict(), FILE)


def load_model(model,model_name):
  device = "cuda" if torch.cuda.is_available() else "cpu"
  FILE = file_path+ str(model_name) + ".pth"
  model.load_state_dict(torch.load(FILE))
  model.to(device)
  model.eval()

resnet18 = models.resnet18()
resnet18.fc = nn.Linear(in_features=512, out_features=5, bias=True)
#print(resnet18)
train_loader , test_loader = set_DataLoader(train_set,test_set,128)#batch_size need to be 128 256
train_loader1 , test_loader = set_DataLoader(train_set,test_set,128)#batch_size need to be 128 256
load_model(resnet18,'9/resnet18')
#train(resnet18,1,18,train_loader,test_loader,train_loader1)
#save_model(resnet18,"10/resnet18")

#torch.cuda.init()
test_acc , prediction_label , groundtruth_label = predicte(resnet18,test_loader)
plot_confusion_matrix(groundtruth_label,prediction_label,normalize="all")

pre_resnet18 = models.resnet18(pretrained=True)
pre_resnet18.fc = nn.Linear(in_features=512, out_features=5, bias=True)
pre_train_loader , pre_test_loader = set_DataLoader(train_set,test_set1,256)#batch_size need to be 128
pre_train_loader1 , pre_test_loader = set_DataLoader(train_set,test_set1,256)#batch_size need to be 128
load_model(pre_resnet18,'5/pre_resnet18')
#train(pre_resnet18,1,18,pre_train_loader,pre_test_loader,pre_train_loader1)
#save_model(pre_resnet18,"10/pre_resnet18")

#torch.cuda.init()
pre_test_acc , pre_prediction_label , pre_groundtruth_label = predicte(pre_resnet18,pre_test_loader)
print(pre_test_acc.item())

plot_confusion_matrix(pre_groundtruth_label,pre_prediction_label,normalize="all")

resnet50 = models.resnet50()
resnet50.fc = nn.Linear(in_features=2048, out_features=5, bias=True)
train_loader , test_loader = set_DataLoader(train_set,test_set,128)#batch_size need to be 32
train_loader1 , test_loader = set_DataLoader(train_set,test_set,128)#batch_size need to be 32
load_model(resnet50,'10/resnet50')
#train(resnet50,1,18,train_loader,test_loader,train_loader1)
#save_model(resnet50,"10/resnet50")

#torch.cuda.init()
test_acc , prediction_label , groundtruth_label = predicte(resnet50,test_loader)
plot_confusion_matrix(groundtruth_label,prediction_label,normalize="all")

pre_resnet50 = models.resnet50(pretrained=True)
pre_resnet50.fc = nn.Linear(in_features=2048, out_features=5, bias=True)
pre_train_loader , pre_test_loader = set_DataLoader(train_set,test_set,128)#batch_size need to be 32
pre_train_loader1 , pre_test_loader = set_DataLoader(train_set,test_set,128)#batch_size need to be 32
load_model(pre_resnet50,'10/pre_resnet50')
#train(pre_resnet50,1,18,pre_train_loader,pre_test_loader,pre_train_loader1)
#save_model(pre_resnet50,"11/pre_resnet50")

#torch.cuda.init()
pre_test_acc , pre_prediction_label , pre_groundtruth_label = predicte(pre_resnet50,pre_test_loader)
plot_confusion_matrix(pre_groundtruth_label,pre_prediction_label,normalize="all")