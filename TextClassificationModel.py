import os
import time
import load_data
import torch
import torch.nn.functional as F
from torch.autograd import Variable
import torch.optim as optim
import numpy as np
from models.LSTM import LSTMClassifier

class TextClassificationModel(object):

    def __init__(self, model):
        self._model = model
        pass

    def _clip_gradient(self, clip_value):
        params = list(filter(lambda p: p.grad is not None, self._model.parameters()))
        for p in params:
            p.grad.data.clamp_(-clip_value, clip_value)
            
    def train(self, train_iter, epoch, loss_fn = F.cross_entropy,
        learning_rate = 2e-5,
            batch_size = 32,
            output_size = 2,
            hidden_size = 256,
            embedding_length = 300):
        total_epoch_loss = 0
        total_epoch_acc = 0
        self._model.cuda()
        optim = torch.optim.Adam(filter(lambda p: p.requires_grad, self._model.parameters()))
        steps = 0
        self._model.train()
        for idx, batch in enumerate(train_iter):
            text = batch.text[0]
            target = batch.label
            target = torch.autograd.Variable(target).long()
            if torch.cuda.is_available():
                text = text.cuda()
                target = target.cuda()
            if (text.size()[0] is not 32):# One of the batch returned by BucketIterator has length different than 32.
                continue
            optim.zero_grad()
            prediction = self._model(text)
            loss = loss_fn(prediction, target)
            num_corrects = (torch.max(prediction, 1)[1].view(target.size()).data == target.data).float().sum()
            acc = 100.0 * num_corrects/len(batch)
            loss.backward()
            self._clip_gradient(1e-1)
            optim.step()
            steps += 1
            
            if steps % 100 == 0:
                print (f'Epoch: {epoch+1}, Idx: {idx+1}, Training Loss: {loss.item():.4f}, Training Accuracy: {acc.item(): .2f}%')
            
            total_epoch_loss += loss.item()
            total_epoch_acc += acc.item()
            
        return total_epoch_loss/len(train_iter), total_epoch_acc/len(train_iter)

    def eval(self, val_iter, score_fn ):
        total_epoch_loss = 0
        total_epoch_acc = 0
        self._model.eval()
        with torch.no_grad():
            for _, batch in enumerate(val_iter):
                text = batch.text[0]
                if (text.size()[0] is not 32):
                    continue
                target = batch.label
                target = torch.autograd.Variable(target).long()
                if torch.cuda.is_available():
                    text = text.cuda()
                    target = target.cuda()
                prediction = self._model(text)
                loss = score_fn(prediction, target)
                num_corrects = (torch.max(prediction, 1)[1].view(target.size()).data == target.data).sum()
                acc = 100.0 * num_corrects/len(batch)
                total_epoch_loss += loss.item()
                total_epoch_acc += acc.item()

        return total_epoch_loss/len(val_iter), total_epoch_acc/len(val_iter)
	