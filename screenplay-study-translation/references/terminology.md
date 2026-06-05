# Terminology

Translate screenplay, camera, and format markers. Keep the English term only when it helps readers learn the format, and pair it with Chinese explanation.

For broader script-format judgment, especially scene numbers, shooting scripts, and reading/spec/public drafts, see `industry_conventions.md`.

## Core Terms

- `INT.`: 内景
- `EXT.`: 外景
- `CUT TO`: 切至
- `CUT TO BLACK`: 切至黑场
- `HARD CUT TO`: 硬切至
- `INSERT SHOT`: 插入镜头
- `TITLE ON SCREEN`: 屏幕字幕
- `DAY FOR NIGHT`: 日拍夜
- `DISSOLVE TO`: 叠化至
- `FADE UP ON`: 淡入至
- `CONT'D`: 续
- `MORE`: 下页续
- `OMITTED`: 本场删去 / 删场

## Voice And Position

Distinguish these terms:

- `V.O.`: 旁白 / 画外叙述. The voice usually does not originate from a currently visible person in the scene.
- `O.S.`: 离画. The speaker is in the same scene space but outside the frame.
- `O.C.`: 离画. Similar to off-camera/off-screen usage.

Do not collapse `V.O.` and `O.S.` into the same Chinese term.

## Unknown Terms

Do not hard-code every possible term into audit logic.

Use layered terminology:

- general terminology knowledge base
- project-specific terms
- author-specific usage notes
- unknown terms report

Unknown terms should usually be `WARN`, not `FAIL`, unless they are source format markers that must be preserved.
