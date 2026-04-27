# TTS Voice & Style Reference

The skill uses [edge-tts](https://github.com/rany2/edge-tts) by default — free, no API key, decent Chinese voices, supports SSML and word-level subtitles.

## Common Chinese voices

| Voice ID                   | Gender | Tone                  | Best for |
|----------------------------|--------|-----------------------|----------|
| `zh-CN-YunjianNeural`      | M      | Deep, sober           | 纪录片 / 体育 / 商业旁白. **Skill default.** |
| `zh-CN-YunxiNeural`        | M      | Younger, casual       | Vlog / 短视频 / 口语化 |
| `zh-CN-YunyangNeural`      | M      | Newscaster            | 新闻 / 严肃 |
| `zh-CN-YunfengNeural`      | M      | Calm, mid-pitch       | 教程 / 知识科普 |
| `zh-CN-XiaoxiaoNeural`     | F      | Versatile, expressive | 通用女声; supports SSML `mstts:express-as` style modulation |
| `zh-CN-XiaoyiNeural`       | F      | Soft, warm            | 治愈系 / lifestyle |
| `zh-CN-XiaohanNeural`      | F      | Mellow                | 故事 / 朗读 |
| `zh-CN-XiaomengNeural`     | F      | Bright young female   | 美食 / 活泼内容 |
| `zh-CN-XiaomoNeural`       | F      | Affectionate          | 情感 / 散文 |
| `zh-CN-liaoning-XiaobeiNeural`     | F | Northeast 东北 dialect | 喜剧 / 接地气 |
| `zh-CN-shaanxi-XiaoniNeural`       | F | Shaanxi 陕西 dialect   | 地方特色内容 |

Multilingual:
- `en-US-JennyNeural`, `en-US-GuyNeural`, `ja-JP-NanamiNeural`, etc.

Full list: `edge-tts --list-voices`.

## Pace and volume

CLI flags on `tts.py`:

| Flag       | Format        | Examples                    |
|------------|---------------|-----------------------------|
| `--rate`   | percentage    | `+0%` (default), `-10%`, `+15%` |
| `--volume` | percentage    | `+0%` (default), `-5%`      |

Useful presets:
- 沉稳纪录片: `--voice zh-CN-YunjianNeural --rate -5%`
- 轻快 vlog: `--voice zh-CN-YunxiNeural --rate +10%`
- 严肃新闻: `--voice zh-CN-YunyangNeural --rate +0%`
- 治愈晚安: `--voice zh-CN-XiaoyiNeural --rate -8%`

## SSML for style modulation

`zh-CN-XiaoxiaoNeural` and a few others support `mstts:express-as` styles. To use them, wrap the script in SSML and pass `--ssml`:

```xml
<speak xmlns="http://www.w3.org/2001/10/synthesis"
       xmlns:mstts="http://www.w3.org/2001/mstts"
       xml:lang="zh-CN">
  <voice name="zh-CN-XiaoxiaoNeural">
    <mstts:express-as style="cheerful" styledegree="1.5">
      今天天气真不错！
    </mstts:express-as>
  </voice>
</speak>
```

Supported styles (Xiaoxiao):
`affectionate`, `angry`, `calm`, `cheerful`, `disgruntled`, `embarrassed`, `fearful`, `gentle`, `lyrical`, `newscast`, `poetry-reading`, `sad`, `serious`, `customerservice`, `assistant`, `chat`, `disgusted`.

`styledegree` 0.01–2.0 (default 1.0) controls intensity.

> The current `tts.py` doesn't expose a `--ssml` flag. To use SSML, prepare the SSML file separately and pipe it through edge-tts directly:
> ```bash
> edge-tts --file ssml.xml --write-media vo.mp3 --write-subtitles vo.srt
> ```
> Then use `vo.mp3` as the voiceover in your spec. SRT-to-sentence-time mapping won't be available; downstream cut planning falls back to file-level timing only.

## Other providers

If edge-tts quality isn't enough, drop in a different provider by replacing the audio file. The skill doesn't care how `vo.mp3` was generated. Strong alternatives for Chinese:

| Provider | Strengths | Notes |
|---|---|---|
| 字节火山引擎 TTS | Top-tier Chinese expressiveness, same family as 剪映 | Paid, AK/SK auth |
| MiniMax T2A v2 | Very natural Chinese, low cost | Paid, API key |
| 阿里云语音合成 | Mature, many voices | Paid |
| ElevenLabs | Best multilingual + voice cloning | Paid, EN-strong |
| OpenAI TTS (gpt-4o-mini-tts) | Good cross-lingual | Paid |

If you adopt one of these, generate `vo.mp3` with their CLI / SDK, then build `vo.json` manually with sentence timings (or skip Mode B's sentence-level mapping and align clips by hand).

## Voice picker decision flow (for the LLM)

When the user says e.g. "找个沉稳点的男声":

1. Map "沉稳/纪录片/男声/旁白" → `zh-CN-YunjianNeural` + `--rate -5%`.
2. Map "活泼/轻快/年轻/vlog" → `zh-CN-YunxiNeural` + `--rate +10%`.
3. Map "新闻/严肃/正式" → `zh-CN-YunyangNeural`.
4. Map "温柔/治愈/晚安" → `zh-CN-XiaoyiNeural` + `--rate -8%`.
5. Map "活泼女声/美食" → `zh-CN-XiaomengNeural`.
6. Map "情感/散文/朗读" → `zh-CN-XiaomoNeural`.
7. Map "搞笑/东北口音" → `zh-CN-liaoning-XiaobeiNeural`.

When in doubt, ask: "我先用 `zh-CN-YunjianNeural` 试一遍？不满意再换。"
