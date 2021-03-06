# ***************************************************************
# Copyright (c) 2020 Jittor. Authors:
#     Guowei Yang <471184555@qq.com>
#     Dun Liang <randonlang@gmail.com>.
#
# All Rights Reserved.
# This file is subject to the terms and conditions defined in
# file 'LICENSE.txt', which is part of this source code package.
# ***************************************************************

import jittor as jt
from jittor.optim import Optimizer
import math

class ReduceLROnPlateau(object):
    def __init__(self, optimizer, mode='min', factor=0.1, patience=10, verbose=False, threshold=1e-4, threshold_mode='rel', cooldown=0, min_lr=0, eps=1e-8):
        assert factor < 1.0, "factor should be < 1.0."
        assert isinstance(optimizer, Optimizer), '{} is not an Optimizer'.format(type(optimizer).__name__)
        assert mode in {'min', 'max'}, 'mode ' + mode + ' is unknown!'
        assert threshold_mode in {'rel', 'abs'},  'threshold mode ' + threshold_mode + ' is unknown!'

        if isinstance(min_lr, list) or isinstance(min_lr, tuple):
            assert len(min_lr) == len(optimizer.param_groups), "expected {} min_lrs, got {}".format(len(optimizer.param_groups), len(min_lr))
            self.min_lrs = list(min_lr)
        else:
            self.min_lrs = [min_lr] * len(optimizer.param_groups)
        self.factor = factor
        self.optimizer = optimizer
        self.patience = patience
        self.verbose = verbose
        self.cooldown = cooldown
        self.n_cd = 0
        self.mode = mode
        self.threshold = threshold
        self.threshold_mode = threshold_mode
        self.loss_best = None
        self.n_bad = 0
        self.eps = eps
        self.last_epoch = 0
        self.loss_best = math.inf if mode=="min" else -math.inf
        
    def step(self, loss, epoch=None):
        # convert `metrics` to float, in case it's a zero-dim Tensor
        loss_now = float(loss)
        if epoch is None:
            epoch = self.last_epoch + 1
        self.last_epoch = epoch

        if self.better(loss_now, self.loss_best):
            self.loss_best = loss_now
            self.n_bad = 0
        else:
            self.n_bad += 1

        if self.n_cd > 0:
            self.n_cd -= 1
            self.n_bad = 0

        if self.n_bad > self.patience:
            self.update_lr(epoch)
            self.n_cd = self.cooldown
            self.n_bad = 0
            
    def update_lr(self, epoch):
        for i, param_group in enumerate(self.optimizer.param_groups):
            old_lr = float(param_group.get("lr", self.optimizer.lr))
            new_lr = max(old_lr * self.factor, self.min_lrs[i])
            if old_lr - new_lr > self.eps:
                if param_group.get("lr")!=None:
                    param_group["lr"] = new_lr
                else:
                    self.optimizer.lr = new_lr
                if self.verbose:
                    print('Epoch {:5d}: reducing learning rate of group {} from {:.4e} to {:.4e}.'.format(epoch, i, old_lr, new_lr))
                          
    def better(self, a, b):
        if self.mode == 'min' and self.threshold_mode == 'rel':
            save = 1.0 - self.threshold
            return a < b * save
        elif self.mode == 'min' and self.threshold_mode == 'abs':
            return a < b - self.threshold
        elif self.mode == 'max' and self.threshold_mode == 'rel':
            save = self.threshold + 1.0
            return a > b * save
        else:
            return a > b + self.threshold