# RadioHub - 技术信息

本手册介绍了RadioHub的关键概念、技术术语和限制。它帮助您理解某些功能为何以特定方式运行。

---

## 播放模式

### HLS模式（默认）

HLS是"HTTP Live Streaming"的缩写。RadioHub通过后端将广播流转换为浏览器可播放的小片段。这使得以下功能成为可能：

- **时移：** 在正在播出的节目中倒退
- **暂停和恢复：** 缓冲区在后台继续运行
- **缓冲录制：** 录制之前收听的内容（HLS-REC）
- **比特率控制：** 根据连接状况自动调整

HLS缓冲区在后端维护。大小可以在[设置 > 常规](#/setup/allgemein/einstellungen)（时移缓冲区）中配置。

### Direct模式

在Direct模式下，浏览器直接连接到电台的原始流。这更加节省资源，但没有时移、暂停或缓冲录制功能。适用于不支持HLS转换的服务器。

---

## 电台列表中的徽章

### ICY（绿色 / 灰色）

**ICY**是"Icecast Metadata"的缩写 - 一种允许电台在流中发送当前标题的协议。当电台支持ICY时，RadioHub会显示当前标题，并可以自动将录音分割为单独的歌曲。

- **ICY（绿色，"good"）：** 电台提供精确的标题变化时间戳。剪切将会干净利落。
- **ICY（绿色，"poor"）：** 电台提供ICY数据，但时间戳不准确（例如延迟报告）。剪切可能会有重叠或间隙。
- **ICY（灰色）：** ICY存在但质量尚未评级。点击可在"good"和"poor"之间切换。

**为什么这很重要？** 一些电台在实际变化后数秒才报告新标题。RadioHub使用音频流中的字节位置进行剪切计算，但如果电台报告延迟，剪切就会偏移。

### AD徽章（广告检测）

RadioHub可以检查电台是否有广告。检查可以在[设置 > 广播 > 电台](#/setup/radio/sender)中启动，分析流URL和服务器响应：

- **0% AD（绿色）：** 检查后无广告嫌疑
- **XX% AD（黄色）：** 以百分比显示广告嫌疑（例如"35% AD"） - 阈值可配置
- **AD（红色）：** 手动标记为广告（隐藏）
- **OK（蓝色）：** 尽管有嫌疑但手动批准

---

## 录制系统

### 分段录制

RadioHub以30分钟为单位进行分段录制。如果与电台的连接断开，最多只会丢失当前片段，而不是整个录音。对于8小时的录音，最多丢失30分钟而不是全部。录制设置（格式、比特率、文件夹）可在[设置 > 录音](#/setup/aufnahmen)中配置。

### 停滞检测

在录制过程中，RadioHub监控文件大小。如果文件30秒内没有增长，录制进程将被检测为"停滞"并重新启动。这可以防止FFmpeg正在运行但不再接收数据的无声录音。

### ICY标题分割

如果电台有ICY元数据，30分钟的片段在录制后会根据检测到的标题变化自动分割为单独的歌曲。没有ICY的情况下，30分钟的块将作为片段保留。

### HTTPS流和重连

许多电台使用HTTPS。FFmpeg的内置重连功能仅在HTTP流中可靠工作。因此，RadioHub自行处理连接断开时的监控和重启，不论协议如何。

---

## 时移和缓冲区

### 时移如何工作？

后端维护一个音频片段的滚动缓冲区。每个片段有几秒钟长。浏览器通过HLS播放列表请求这些片段。倒退时，从缓冲区加载较旧的片段。

### 缓冲录制（HLS-REC）

缓冲录制使用现有的HLS缓冲区。当您开始录制时，RadioHub可以包含缓冲区中过去X分钟的内容。回溯时间可在[设置 > 常规](#/setup/allgemein/einstellungen)（HLS录音）中配置。这允许录制正在播放的歌曲。

---

## 剪辑器（编辑工具）

### 波形

波形显示是从音频数据（峰值）计算得出的。它显示随时间变化的音量，有助于精确放置剪切点。

### 标记

标记是波形中的剪切点。它们可以手动设置或从ICY标题变化中自动获取。剪切时，录音会在这些点被分割为片段。

### 过渡分析

分析检查每个标记周围的音频区域。它评估过渡是否干净（标题之间有静音）或有问题（例如两个标题重叠的交叉淡入淡出）。颜色：绿色 = 良好，黄色 = 需检查，红色 = 有问题。

### 标准化（EBU R128）

标准化将音量调整到EBU R128标准 - 用于一致响度的欧洲广播标准。这样，无论电台的原始音量如何，所有片段听起来都一样响亮。

---

## 播客系统

### 自动下载

订阅的播客可以自动下载新剧集。间隔可在[设置 > 播客](#/setup/podcast)中配置。下载存储在本地，可离线使用。

### 订阅源更新

播客订阅源通过RSS/Atom查询。[更新间隔](#/setup/podcast)决定RadioHub检查新剧集的频率。

---

## 存储和数据

在[设置 > 存储](#/setup/speicher)中，可以配置录音、播客和缓存的存储路径。显示每个区域的已用和可用空间。

外部数据源（Radio-Browser API、Podcast Index）在[设置 > 服务](#/setup/dienste)中可见，如果需要可以切换到自己的实例。

---

## 自动后台进程

RadioHub运行多个无需用户交互即可工作的后台进程：

### 播客订阅源更新

RadioHub启动时，会启动一个定期后台进程，自动检查所有订阅的播客订阅源是否有新剧集。间隔（默认：6小时）可在[设置 > 播客](#/setup/podcast)中配置。启用自动下载后，新剧集将自动下载。

### HLS缓冲区管理

在HLS模式下播放电台时，后端会启动一个FFmpeg进程，将音频流分割为短片段（每段1秒）。这些形成一个10分钟的滚动缓冲区。同时运行一个ICY元数据记录器，检测流中的标题变化。两个进程在停止播放时自动结束。

### 录制监控

在活跃录制期间，运行两个监控进程：

- **停滞检测：** 每30秒检查录制文件是否在增长。连续三次检查没有增长（90秒）将触发录制进程重启。
- **存储监控：** 定期检查可用磁盘空间。如果低于100 MB，录制将自动停止以防止数据丢失。

### HLS缓冲录制（HLS-REC）

在HLS缓冲录制期间，收集器进程每0.5秒从HLS缓冲区复制新片段到录制目录。启动时，配置的回溯分钟数会从现有缓冲区中额外获取。停止时，片段会自动合并，如果有ICY数据可用，则分割为单独的标题。

### 网站图标缓存

加载电台列表时，缺失的电台图标会在后台下载并在本地缓存。此过程静默运行，不影响界面。

### 比特率检测

首次播放电台时，RadioHub通过FFprobe检查实际比特率和编解码器。结果会保存并显示在电台列表中。在[设置 > 广播 > 电台](#/setup/radio/sender)中，可以启动所有电台的批量检查。

---

## 已知限制

- **时移仅在HLS模式下可用：** Direct流以1:1直通，没有缓冲。
- **ICY质量参差不齐：** 一些电台提供不准确或延迟的元数据。这会影响剪切精度。
- **SSL证书：** 一些电台使用特殊的SSL配置。RadioHub会在需要时绕过，但可能会出现警告。
- **长时间录制：** 连接中断时最多丢失30分钟（一个片段）。旧片段会被保留。
- **浏览器限制：** 浏览器中的Web Audio API只能在音频上下文激活时提供VU表数据。一些浏览器需要用户交互。

---

## 参考资料

献给技术爱好者 - RadioHub背后的技术和标准：

### 流媒体协议

- [HTTP Live Streaming (HLS)](https://zh.wikipedia.org/wiki/HTTP_Live_Streaming) - RadioHub用于时移的Apple自适应流媒体协议
- [Icecast](https://zh.wikipedia.org/wiki/Icecast) - 推广了ICY元数据协议的开源流媒体服务器
- [SHOUTcast / ICY协议](https://zh.wikipedia.org/wiki/SHOUTcast) - 流中标题信息的ICY元数据标准的起源
- [网络电台](https://zh.wikipedia.org/wiki/%E7%BD%91%E7%BB%9C%E7%94%B5%E5%8F%B0) - 互联网上广播流媒体的概述

### 音频格式和编解码器

- [MP3 (MPEG-1 Audio Layer 3)](https://zh.wikipedia.org/wiki/MP3) - 广播流中最常见的音频格式
- [AAC (Advanced Audio Coding)](https://zh.wikipedia.org/wiki/%E9%80%B2%E9%9A%8E%E9%9F%B3%E8%A8%8A%E7%B7%A8%E7%A2%BC) - 在相同比特率下质量更好的现代编解码器
- [Ogg Vorbis](https://zh.wikipedia.org/wiki/Vorbis) - 免费开放的音频编解码器
- [FLAC (Free Lossless Audio Codec)](https://zh.wikipedia.org/wiki/FLAC) - 最高质量的无损压缩

### 音频处理

- [EBU R128](https://en.wikipedia.org/wiki/EBU_R_128) - 用于广播响度标准化的欧洲标准
- [FFmpeg](https://zh.wikipedia.org/wiki/FFmpeg) - RadioHub用于转换、录制和剪切的核心多媒体框架
- [Web Audio API](https://developer.mozilla.org/zh-CN/docs/Web/API/Web_Audio_API) - 用于音频分析（VU表、波形）的浏览器接口

### 数据源

- [Radio-Browser API](https://www.radio-browser.info/) - 拥有超过30,000个全球电台的开放社区数据库
- [Podcast Index](https://podcastindex.org/) - 作为专有目录替代的开放播客目录
- [RSS (Really Simple Syndication)](https://zh.wikipedia.org/wiki/RSS) - 播客提供新剧集的订阅源格式

### 技术基础

- [比特率](https://zh.wikipedia.org/wiki/%E6%AF%94%E7%89%B9%E7%8E%87) - 音频流的数据速率（例如128 kbps、320 kbps）
- [流媒体](https://zh.wikipedia.org/wiki/%E6%B5%81%E5%AA%92%E4%BD%93) - 实时数据传输的基础
- [音频数据压缩](https://zh.wikipedia.org/wiki/%E9%9F%B3%E9%A2%91%E7%BC%96%E7%A0%81) - 有损压缩的工作原理
- [SSL/TLS](https://zh.wikipedia.org/wiki/%E5%82%B3%E8%BC%B8%E5%B1%A4%E5%AE%89%E5%85%A8%E6%80%A7%E5%8D%94%E5%AE%9A) - HTTPS流中使用的加密
