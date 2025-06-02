# File: carn.py
"""
CARN 超分辨率模型（x3 放大）
基于论文《Fast, Accurate, and Lightweight Super‑Resolution with Cascading Residual Network》
"""

import torch
import torch.nn as nn

class ResidualBlock(nn.Module):
    """
    基础残差块：两层 3×3 卷积 + ReLU，输入跳连
    """
    def __init__(self, channels):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.relu  = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)

    def forward(self, x):
        identity = x
        out = self.relu(self.conv1(x))
        out = self.conv2(out)
        return out + identity

class CARN(nn.Module):
    """
    级联残差网络 (CARN)：
    - scale: 放大倍数（此处默认 3）
    - num_channels: 输入/输出通道数（RGB=3）
    - num_features: 特征图通道数
    - num_cascade: 级联残差块数量
    """
    def __init__(self, scale=3, num_channels=3, num_features=64, num_cascade=3):
        super(CARN, self).__init__()
        # Entry 卷积：RGB -> 特征空间
        self.entry = nn.Conv2d(num_channels, num_features, kernel_size=3, padding=1)
        # 级联残差块
        self.cascade_blocks = nn.ModuleList(
            [ResidualBlock(num_features) for _ in range(num_cascade)]
        )
        # 拼接后降维
        self.mid = nn.Conv2d(num_features * num_cascade, num_features,
                             kernel_size=1, padding=0)
        # 上采样：卷积 -> PixelShuffle -> 卷积 -> RGB
        self.upsampler = nn.Sequential(
            nn.Conv2d(num_features, num_features * (scale ** 2),
                      kernel_size=3, padding=1),
            nn.PixelShuffle(scale),
            nn.Conv2d(num_features, num_channels,
                      kernel_size=3, padding=1)
        )

    def forward(self, x):
        out = self.entry(x)
        feats = []
        for block in self.cascade_blocks:
            out = block(out)
            feats.append(out)
        # 拼接 & 降维
        out = torch.cat(feats, dim=1)
        out = self.mid(out)
        # 上采样
        out = self.upsampler(out)
        return out
