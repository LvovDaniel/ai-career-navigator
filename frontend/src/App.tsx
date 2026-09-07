import { useEffect, useRef, useState } from 'react'
import type { MouseEvent } from 'react'
import './App.css'

const API_BASE_URL =
  import.meta.env.VITE_API_URL || 'http://localhost:8000'

// =========================================================
// ICONS FOR PROFESSIONS
// =========================================================

const professionIcons: Record<string, string> = {
  'Backend Developer': '🖥️',
  'Frontend Developer': '🎨',
  'Fullstack Developer': '🧩',
  'Python Developer': '🐍',
  'C++ Developer': '⚙️',
  'Java Developer': '☕',
  'JavaScript Developer': '🟨',
  'TypeScript Developer': '🔷',
  'Data Analyst': '📊',
  'Data Scientist': '🔬',
  'System Analyst': '🧠',
  'Business Analyst': '📋',
  'DevOps Engineer': '🚀',
  'QA Engineer': '🧪',
  'Software Engineer': '💻',
  'ML Engineer': '🤖',
  'Machine Learning Engineer': '🧬',
}

function App() {
  const [goal, setGoal] = useState('')
  const [skills, setSkills] = useState('')
  const [experience, setExperience] = useState('')

  const [professions, setProfessions] = useState<string[]>([])
  const [professionsLoading, setProfessionsLoading] = useState(true)

  // =========================================================
  // CUSTOM PROFESSION DROPDOWN
  // =========================================================

  const [professionOpen, setProfessionOpen] = useState(false)
  const [professionSearch, setProfessionSearch] = useState('')

  const professionDropdownRef =
    useRef<HTMLDivElement | null>(null)

  const [skillLevels, setSkillLevels] =
    useState<Record<string, number>>({})

  const [loading, setLoading] = useState(false)

  const [result, setResult] =
    useState<any>(null)

  const [history, setHistory] =
    useState<any[]>([])

  const [selectedCareerPath, setSelectedCareerPath] =
    useState<string | null>(null)

  // =========================================================
  // CLOSE PROFESSION DROPDOWN WHEN CLICKING OUTSIDE
  // =========================================================

  useEffect(() => {
    const handleClickOutside = (event: globalThis.MouseEvent) => {
      if (
        professionDropdownRef.current &&
        !professionDropdownRef.current.contains(
          event.target as Node
        )
      ) {
        setProfessionOpen(false)
      }
    }

    document.addEventListener(
      'mousedown',
      handleClickOutside
    )

    return () => {
      document.removeEventListener(
        'mousedown',
        handleClickOutside
      )
    }
  }, [])

  // =========================================================
  // ERROR MESSAGE
  // =========================================================

  const getErrorMessage = (
    errorData: any,
    fallback: string
  ) => {
    if (typeof errorData?.detail === 'string') {
      return errorData.detail
    }

    return fallback
  }

  // =========================================================
  // GET PROFESSIONS
  // =========================================================

  const getProfessions = async (): Promise<string[]> => {
    const response = await fetch(
      `${API_BASE_URL}/professions`
    )

    if (!response.ok) {
      throw new Error(
        'Не удалось получить список профессий.'
      )
    }

    const data = await response.json()

    if (!Array.isArray(data.professions)) {
      throw new Error(
        'Backend не вернул список профессий.'
      )
    }

    return data.professions
  }

  // =========================================================
  // LOAD PROFESSIONS
  // =========================================================

  useEffect(() => {
    const loadProfessions = async () => {
      try {
        setProfessionsLoading(true)

        const data = await getProfessions()

        setProfessions(data)
      } catch (error) {
        console.error(
          'Ошибка загрузки профессий:',
          error
        )

        alert(
          'Не удалось загрузить список профессий. Проверь, запущен ли Backend.'
        )
      } finally {
        setProfessionsLoading(false)
      }
    }

    loadProfessions()
  }, [])

  // =========================================================
  // NORMALIZE PROFESSION
  // =========================================================

  const normalizeProfession = (
    value: string
  ) => {
    return value
      .trim()
      .toLowerCase()
      .replace(/\s+/g, ' ')
  }

  // =========================================================
  // CHECK PROFESSION
  // =========================================================

  const isProfessionAllowed = async (
    profession: string
  ) => {
    const normalizedInput =
      normalizeProfession(profession)

    return professions.some(
      (item: string) =>
        normalizeProfession(item) ===
        normalizedInput
    )
  }

  // =========================================================
  // FILTER PROFESSIONS
  // =========================================================

  const filteredProfessions =
    professions.filter((profession) =>
      profession
        .toLowerCase()
        .includes(
          professionSearch
            .trim()
            .toLowerCase()
        )
    )

  // =========================================================
  // SELECT PROFESSION
  // =========================================================

  const selectProfession = (
    profession: string
  ) => {
    setGoal(profession)
    setProfessionSearch('')
    setProfessionOpen(false)
  }

  // =========================================================
  // INPUT VALIDATION
  // =========================================================

  const isValidInput = (
    text: string,
    required: boolean = false
  ) => {
    const value = text.trim()

    if (!value) {
      return !required
    }

    if (value.length < 2) {
      return false
    }

    if (!/[a-zA-Zа-яА-ЯёЁ]/.test(value)) {
      return false
    }

    const normalized =
      value
        .toLowerCase()
        .replace(/[^a-zа-яё0-9]/gi, '')

    if (!normalized) {
      return false
    }

    if (normalized.length >= 8) {
      const uniqueCharacters =
        new Set(normalized).size

      if (uniqueCharacters <= 2) {
        return false
      }
    }

    if (normalized.length >= 6) {
      for (
        const char of new Set(normalized)
      ) {
        if (
          normalized.includes(
            char.repeat(6)
          )
        ) {
          return false
        }
      }
    }

    return true
  }

  // =========================================================
  // FORM VALIDATION
  // =========================================================

  const validateForm = () => {
    const goalText = goal.trim()
    const skillsText = skills.trim()
    const experienceText =
      experience.trim()

    if (!goalText) {
      return 'Выбери желаемую профессию.'
    }

    if (!isValidInput(goalText, true)) {
      return 'Ошибка. Проверьте введённые данные и попробуйте ещё раз.'
    }

    if (
      skillsText &&
      !isValidInput(skillsText)
    ) {
      return 'Ошибка. Проверьте введённые данные и попробуйте ещё раз.'
    }

    if (
      experienceText &&
      !isValidInput(experienceText)
    ) {
      return 'Ошибка. Проверьте введённые данные и попробуйте ещё раз.'
    }

    const enteredSkills =
      skillsText
        .split(',')
        .map((skill) => skill.trim())
        .filter(
          (skill) => skill.length > 0
        )

    for (const skill of enteredSkills) {
      if (!isValidInput(skill)) {
        return 'Ошибка. Проверьте введённые данные и попробуйте ещё раз.'
      }
    }

    return null
  }

  // =========================================================
  // SKILLS
  // =========================================================

  const skillList = skills
    .split(',')
    .map((skill) => skill.trim())
    .filter(
      (skill) => skill.length > 0
    )

  // =========================================================
  // USER ID
  // =========================================================

  const getStoredUserId = () => {
    return Number(
      localStorage.getItem(
        'career_navigator_user_id'
      )
    )
  }

  // =========================================================
  // LOAD HISTORY
  // =========================================================

  const loadHistory = async (
    userId: number
  ) => {
    try {
      const response =
        await fetch(
          `${API_BASE_URL}/roadmaps/${userId}`
        )

      if (!response.ok) {
        return
      }

      const data =
        await response.json()

      setHistory(
        Array.isArray(data.history)
          ? data.history
          : []
      )
    } catch (error) {
      console.error(
        'Ошибка загрузки истории:',
        error
      )
    }
  }

  // =========================================================
  // CREATE USER
  // =========================================================

  const createUser = async (
    selectedGoal: string
  ) => {
    const response =
      await fetch(
        `${API_BASE_URL}/users`,
        {
          method: 'POST',
          headers: {
            'Content-Type':
              'application/json',
          },
          body: JSON.stringify({
            name: 'Danya',
            email:
              `danya_${Date.now()}@test.com`,
            resume: experience,
            goal: selectedGoal,
          }),
        }
      )

    if (!response.ok) {
      let message =
        'Не удалось создать пользователя.'

      try {
        const errorData =
          await response.json()

        message =
          getErrorMessage(
            errorData,
            message
          )
      } catch {
        //
      }

      throw new Error(message)
    }

    const user =
      await response.json()

    const userId =
      Number(user.user_id)

    if (!userId) {
      throw new Error(
        'Backend не вернул user_id.'
      )
    }

    localStorage.setItem(
      'career_navigator_user_id',
      String(userId)
    )

    return userId
  }

  // =========================================================
  // SAVE SKILLS
  // =========================================================

  const saveSkills = async (
    userId: number
  ) => {
    // Полностью синхронизируем навыки с тем,
    // что сейчас указано пользователем.
    // Старые навыки из БД будут удалены backend'ом.
    const uniqueSkills = Array.from(
      new Set(
        skillList
          .map((skill) => skill.trim())
          .filter((skill) => skill.length > 0)
      )
    )

    const response = await fetch(
      `${API_BASE_URL}/skills/${userId}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          skills: uniqueSkills.map((skill) => ({
            user_id: userId,
            skill,
            level: skillLevels[skill] || 3,
          })),
        }),
      }
    )

    if (!response.ok) {
      let message =
        'Не удалось синхронизировать навыки.'

      try {
        const errorData =
          await response.json()

        message = getErrorMessage(
          errorData,
          message
        )
      } catch {
        //
      }

      throw new Error(message)
    }
  }

  // =========================================================
  // SAVE PROFILE
  // =========================================================

  const saveProfile = async (
    userId: number,
    selectedGoal: string
  ) => {
    const response =
      await fetch(
        `${API_BASE_URL}/profile`,
        {
          method: 'POST',
          headers: {
            'Content-Type':
              'application/json',
          },
          body: JSON.stringify({
            user_id: userId,
            goal: selectedGoal,
            skills: skillList,
            experience,
            projects:
              experience.trim()
                ? [experience.trim()]
                : [],
          }),
        }
      )

    if (!response.ok) {
      let message =
        'Не удалось сохранить профиль.'

      try {
        const errorData =
          await response.json()

        message =
          getErrorMessage(
            errorData,
            message
          )
      } catch {
        //
      }

      throw new Error(message)
    }
  }

  // =========================================================
  // RUN AI ANALYSIS
  // =========================================================

  const runAnalysis = async (
    userId: number
  ) => {
    const response =
      await fetch(
        `${API_BASE_URL}/analyze?user_id=${userId}`,
        {
          method: 'POST',
        }
      )

    if (!response.ok) {
      let message =
        'Ошибка. Проверьте введённые данные и попробуйте ещё раз.'

      try {
        const errorData =
          await response.json()

        message =
          getErrorMessage(
            errorData,
            message
          )
      } catch {
        //
      }

      throw new Error(message)
    }

    const data =
      await response.json()

    console.log(
      'AI RESULT:',
      data
    )

    return data
  }

  // =========================================================
  // SCROLL TO RESULT
  // =========================================================

  const scrollToResult = () => {
    setTimeout(() => {
      document
        .querySelector('.result')
        ?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        })
    }, 200)
  }

  // =========================================================
  // ANALYZE CAREER
  // =========================================================

  const analyzeCareer = async () => {
    const validationError =
      validateForm()

    if (validationError) {
      setResult(null)
      setSelectedCareerPath(null)

      alert(validationError)
      return
    }

    const selectedGoal =
      goal.trim()

    if (!selectedGoal) {
      alert(
        'Выбери желаемую профессию.'
      )
      return
    }

    if (professionsLoading) {
      alert(
        'Список профессий ещё загружается. Подожди немного.'
      )
      return
    }

    setLoading(true)
    setResult(null)
    setSelectedCareerPath(null)

    try {
      // CHECK PROFESSION

      const professionAllowed =
        await isProfessionAllowed(
          selectedGoal
        )

      if (!professionAllowed) {
        throw new Error(
          `Профессия "${selectedGoal}" отсутствует в списке доступных профессий. Выбери профессию из списка.`
        )
      }

      // USER

      let userId =
        getStoredUserId()

      if (!userId) {
        userId =
          await createUser(
            selectedGoal
          )
      }

      // SAVE SKILLS

      await saveSkills(userId)

      // SAVE PROFILE

      await saveProfile(
        userId,
        selectedGoal
      )

      // AI

      const data =
        await runAnalysis(userId)

      setResult(data)

      // HISTORY

      await loadHistory(userId)

      scrollToResult()

    } catch (error) {
      console.error(
        'ОШИБКА:',
        error
      )

      if (
        error instanceof TypeError
      ) {
        alert(
          `Frontend не может подключиться к Backend.

Проверь адрес:
${API_BASE_URL}`
        )
      } else {
        alert(
          error instanceof Error
            ? error.message
            : 'Ошибка. Проверьте введённые данные и попробуйте ещё раз.'
        )
      }
    } finally {
      setLoading(false)
    }
  }

  // =========================================================
  // CAREER MATCH
  // =========================================================

  const calculateCareerMatch = () => {
    if (!result) {
      return 0
    }

    if (
      typeof result.career_match_percent ===
      'number'
    ) {
      return Math.round(
        Math.max(
          0,
          Math.min(
            100,
            result.career_match_percent
          )
        )
      )
    }

    const missingSkills =
      Array.isArray(
        result.missing_skills
      )
        ? result.missing_skills
        : []

    if (
      missingSkills.length === 0
    ) {
      return 100
    }

    let totalProgress = 0

    for (
      const item of missingSkills
    ) {
      const currentLevel =
        Number(
          item?.current_level ?? 0
        )

      const requiredLevel =
        Number(
          item?.required_level ?? 5
        )

      if (requiredLevel > 0) {
        totalProgress +=
          Math.min(
            100,
            (
              currentLevel /
              requiredLevel
            ) * 100
          )
      }
    }

    return Math.round(
      Math.max(
        0,
        Math.min(
          100,
          totalProgress /
            missingSkills.length
        )
      )
    )
  }

  const careerMatch =
    calculateCareerMatch()

  // =========================================================
  // CAREER DYNAMICS
  // =========================================================

  const getCareerDynamics = () => {
    if (history.length < 2) {
      return null
    }

    const currentMatch =
      Number(
        history[0]
          ?.career_match_percent ?? 0
      )

    const previousMatch =
      Number(
        history[1]
          ?.career_match_percent ?? 0
      )

    return {
      currentMatch,
      previousMatch,
      difference:
        currentMatch -
        previousMatch,
    }
  }

  const careerDynamics =
    getCareerDynamics()

 // =========================================================
// SELECT CAREER PATH
// =========================================================

const selectCareerPath = (
  event: MouseEvent<HTMLButtonElement>,
  path: any
) => {
  event.stopPropagation()

  const selectedRole =
    path?.title ||
    path?.role

  if (!selectedRole) {
    alert(
      'Не удалось определить выбранное направление.'
    )
    return
  }

  const selectedRoleText =
    String(selectedRole).trim()

  if (!selectedRoleText) {
    return
  }

  setGoal(selectedRoleText)
  setSelectedCareerPath(null)

  window.scrollTo({
    top: 0,
    behavior: 'smooth',
  })
}
  // =========================================================
  // RENDER
  // =========================================================

  return (
    <div className="app">

      {/* HEADER */}

      <header className="header">

        <div className="logo">
          AI Career Navigator
        </div>

        <div className="subtitle">
          Твой персональный навигатор в карьере
        </div>

      </header>

      {/* MAIN */}

      <main className="container">

        {/* HERO */}

        <section className="hero">

          <div className="hero-badge">
            AI CAREER NAVIGATOR
          </div>

          <h1>
            Построй карьерный путь
            с помощью AI
          </h1>

          <p>
            Расскажи о своих навыках и цели —
            система определит пробелы,
            оценит готовность и построит
            персональный карьерный маршрут.
          </p>

        </section>

        {/* FORM */}

        <section className="card">

          <div className="form-heading">

            <div className="form-number">
              01
            </div>

            <div className="form-heading-content">

              <h2>
                Расскажи о себе
              </h2>

              <p>
                Чем больше информации ты укажешь,
                тем точнее будет анализ.
              </p>

            </div>

          </div>

          {/* =================================================
              CUSTOM PROFESSION SELECT
          ================================================= */}

          <label>
            Желаемая профессия
          </label>

          <div
            className="profession-select-wrapper"
            ref={professionDropdownRef}
          >

            {/* SELECT BUTTON */}

            <button
              type="button"
              className={
                `profession-select ${
                  professionOpen
                    ? 'profession-select-open'
                    : ''
                }`
              }
              onClick={() => {
                if (
                  !professionsLoading &&
                  !loading
                ) {
                  setProfessionOpen(
                    !professionOpen
                  )
                }
              }}
              disabled={
                professionsLoading ||
                loading
              }
            >

              <span className="profession-select-left">

                <span className="profession-main-icon">
                  {goal
                    ? professionIcons[goal] ||
                      '💼'
                    : '💼'}
                </span>

                <span
                  className={
                    goal
                      ? 'profession-selected-text'
                      : 'profession-placeholder'
                  }
                >
                  {professionsLoading
                    ? 'Загрузка профессий...'
                    : goal ||
                      'Выбери профессию'}
                </span>

              </span>

              <span
                className={
                  `profession-chevron ${
                    professionOpen
                      ? 'profession-chevron-open'
                      : ''
                  }`
                }
              >
                ↓
              </span>

            </button>

            {/* DROPDOWN */}

            {professionOpen && (
              <div className="profession-dropdown">

                {/* SEARCH */}

                <div className="profession-search-wrapper">

                  <span className="profession-search-icon">
                    🔍
                  </span>

                  <input
                    type="text"
                    className="profession-search"
                    placeholder="Поиск профессии..."
                    value={professionSearch}
                    onChange={(e) =>
                      setProfessionSearch(
                        e.target.value
                      )
                    }
                    autoFocus
                  />

                </div>

                {/* LIST */}

                <div className="profession-list">

                  {filteredProfessions.length >
                    0 ? (
                    filteredProfessions.map(
                      (profession) => {

                        const isSelected =
                          goal ===
                          profession

                        return (
                          <button
                            type="button"
                            key={profession}
                            className={
                              `profession-option ${
                                isSelected
                                  ? 'profession-option-selected'
                                  : ''
                              }`
                            }
                            onClick={() =>
                              selectProfession(
                                profession
                              )
                            }
                          >

                            <span className="profession-option-icon">
                              {professionIcons[
                                profession
                              ] || '💼'}
                            </span>

                            <span className="profession-option-name">
                              {profession}
                            </span>

                            {isSelected && (
                              <span className="profession-option-check">
                                ✓
                              </span>
                            )}

                          </button>
                        )
                      }
                    )
                  ) : (

                    <div className="profession-empty">
                      <span>
                        🔎
                      </span>

                      <p>
                        Профессия не найдена
                      </p>

                      <small>
                        Попробуй изменить запрос
                      </small>
                    </div>

                  )}

                </div>

              </div>
            )}

          </div>

          {!professionsLoading &&
            professions.length > 0 && (
              <p className="form-hint">
                Доступно профессий:{' '}
                {professions.length}
              </p>
            )}

          {/* =================================================
              SKILLS
          ================================================= */}

          <label>
            Текущие навыки
          </label>

          <textarea
            placeholder="Например: Python, C++, Git, SQL"
            value={skills}
            onChange={(e) =>
              setSkills(e.target.value)
            }
          />

          {/* =================================================
              SKILL LEVELS
          ================================================= */}

          {skillList.length > 0 && (

            <div className="skill-levels">

              <label>
                Уровень навыков
              </label>

              {skillList.map(
                (skill) => (

                  <div
                    className="skill-level-row"
                    key={skill}
                  >

                    <strong>
                      {skill}
                    </strong>

                    <select
                      value={
                        skillLevels[skill] || 3
                      }
                      onChange={(e) =>
                        setSkillLevels({
                          ...skillLevels,
                          [skill]:
                            Number(
                              e.target.value
                            ),
                        })
                      }
                    >

                      <option value={1}>
                        1 — Начальный
                      </option>

                      <option value={2}>
                        2 — Базовый
                      </option>

                      <option value={3}>
                        3 — Средний
                      </option>

                      <option value={4}>
                        4 — Продвинутый
                      </option>

                      <option value={5}>
                        5 — Эксперт
                      </option>

                    </select>

                  </div>
                )
              )}

            </div>
          )}

          {/* =================================================
              EXPERIENCE
          ================================================= */}

          <label>
            Опыт и проекты
          </label>

          <textarea
            placeholder="Расскажи о своём опыте, проектах и обучении"
            value={experience}
            onChange={(e) =>
              setExperience(e.target.value)
            }
          />

          {/* =================================================
              BUTTON
          ================================================= */}

          <button
            type="button"
            onClick={analyzeCareer}
            disabled={
              loading ||
              !goal.trim() ||
              professionsLoading
            }
          >
            {loading
              ? 'Анализируем...'
              : 'Построить карьерный маршрут →'}
          </button>

        </section>

        {/* =================================================
            RESULT
        ================================================= */}

        {result && (

          <section className="result">

            <div className="result-heading">

              <div className="result-number">
                02
              </div>

              <div className="result-heading-content">

                <h2>
                  Твой карьерный маршрут
                </h2>

                <p>
                  Анализ профиля, навыков и
                  требований целевой профессии.
                </p>

              </div>

            </div>

            {/* TARGET + LEVEL */}

            <div className="result-grid">

              <div className="result-card">

                <span className="result-label">
                  Целевая профессия
                </span>

                <h3>
                  {result.target_role}
                </h3>

              </div>

              <div className="result-card">

                <span className="result-label">
                  Текущий уровень
                </span>

                <h3>
                  {result.current_level}
                </h3>

              </div>

            </div>

            {/* STRENGTHS */}

            <div className="result-card">

              <h3>
                Сильные стороны
              </h3>

              <ul className="result-list">

                {Array.isArray(
                  result.strengths
                ) &&
                  result.strengths.map(
                    (
                      item: any,
                      index: number
                    ) => (

                      <li key={index}>

                        {typeof item === 'object'
                          ? `${item.skill}: уровень ${item.level}`
                          : item}

                      </li>

                    )
                  )}

              </ul>

            </div>

            {/* MISSING SKILLS */}

            <div className="result-card">

              <h3>
                Что нужно изучить
              </h3>

              <div className="skills-list">

                {Array.isArray(
                  result.missing_skills
                ) &&
                  result.missing_skills.map(
                    (
                      item: any,
                      index: number
                    ) => {

                      const currentLevel =
                        Number(
                          item?.current_level ?? 0
                        )

                      const requiredLevel =
                        Number(
                          item?.required_level ?? 5
                        )

                      const progress =
                        requiredLevel > 0
                          ? Math.min(
                              100,
                              (
                                currentLevel /
                                requiredLevel
                              ) * 100
                            )
                          : 0

                      return (

                        <div
                          className="skill-item"
                          key={index}
                        >

                          <div className="skill-header">

                            <strong>
                              {item?.skill}
                            </strong>

                            <span>
                              {currentLevel}
                              {' / '}
                              {requiredLevel}
                            </span>

                          </div>

                          <div className="progress">

                            <div
                              className="progress-bar"
                              style={{
                                width:
                                  `${progress}%`,
                              }}
                            />

                          </div>

                          <p>
                            {item?.reason}
                          </p>

                        </div>
                      )
                    }
                  )}

              </div>

            </div>

            {/* RECOMMENDED PROJECT */}

            <div className="result-card">

              <h3>
                Рекомендуемый проект
              </h3>

              <p>
                {typeof result.recommended_project ===
                'string'
                  ? result.recommended_project
                  : result.recommended_project
                      ?.description ||
                    result.recommended_project
                      ?.name ||
                    'Проект пока не сформирован.'}
              </p>

              {result.recommended_project
                ?.technologies &&
                Array.isArray(
                  result.recommended_project
                    .technologies
                ) && (

                  <div className="tags">

                    {result.recommended_project
                      .technologies
                      .map(
                        (
                          technology: string,
                          index: number
                        ) => (

                          <span key={index}>
                            {technology}
                          </span>

                        )
                      )}

                  </div>
                )}

            </div>

            {/* CAREER MATCH */}

            <div className="result-card career-match-card">

              <div className="career-match-header">

                <div>

                  <span className="result-label">
                    КАРЬЕРНЫЙ MATCH
                  </span>

                  <h3>
                    Готовность к целевой профессии
                  </h3>

                </div>

                <div className="career-match-value">
                  {careerMatch}%
                </div>

              </div>

              <div className="career-match-bar">

                <div
                  className="career-match-progress"
                  style={{
                    width:
                      `${careerMatch}%`,
                  }}
                />

              </div>

              <p>
                Показатель отражает соответствие
                текущих навыков требованиям
                выбранной профессии.
              </p>

            </div>

            {/* CAREER DYNAMICS */}

            {careerDynamics && (

              <div className="result-card career-dynamics">

                <span className="result-label">
                  ДИНАМИКА CAREER MATCH
                </span>

                <h3>
                  Твой прогресс
                </h3>

                <div className="career-dynamics-values">

                  <div className="career-dynamics-item">

                    <span>
                      Было
                    </span>

                    <strong>
                      {careerDynamics.previousMatch}%
                    </strong>

                  </div>

                  <div className="career-dynamics-arrow">
                    →
                  </div>

                  <div className="career-dynamics-item">

                    <span>
                      Стало
                    </span>

                    <strong>
                      {careerDynamics.currentMatch}%
                    </strong>

                  </div>

                </div>

                <p className="career-dynamics-growth">

                  {careerDynamics.difference >= 0
                    ? '+'
                    : ''}

                  {careerDynamics.difference}
                  {' '}
                  процентных пунктов

                </p>

              </div>
            )}

            {/* CAREER PATHS */}

            {Array.isArray(
              result.career_paths
            ) &&
              result.career_paths.length > 0 && (

                <div className="result-card career-paths-card">

                  <span className="result-label">
                    КАРЬЕРНЫЕ ПУТИ
                  </span>

                  <h3>
                    Куда можно двигаться дальше
                  </h3>

                  <p>
                    AI определил несколько направлений,
                    которые подходят тебе на основе
                    текущего профиля.
                  </p>

                  <div className="career-paths">

                    {result.career_paths
                      .slice(0, 3)
                      .map(
                        (
                          path: any,
                          index: number
                        ) => {

                          const pathId =
                            `ai-path-${index}`

                          const pathTitle =
                            path?.title ||
                            path?.role ||
                            'Карьерное направление'

                          const requiredSkills =
                            Array.isArray(
                              path?.required_skills
                            )
                              ? path.required_skills
                              : []

                          const missingSkills =
                            Array.isArray(
                              path?.missing_skills
                            )
                              ? path.missing_skills
                              : []

                          return (

                            <div
                              className={
                                `career-path ${
                                  selectedCareerPath ===
                                  pathId
                                    ? 'career-path-selected'
                                    : ''
                                }`
                              }
                              key={pathId}
                              onClick={() =>
                                setSelectedCareerPath(
                                  selectedCareerPath ===
                                    pathId
                                    ? null
                                    : pathId
                                )
                              }
                            >

                              <div className="career-path-top">

                                <div className="career-path-icon">

                                  {index === 0
                                    ? '⚙️'
                                    : index === 1
                                      ? '🧠'
                                      : '🚀'}

                                </div>

                                <div>

                                  <h4>
                                    {pathTitle}
                                  </h4>

                                  <p>
                                    {path?.why ||
                                      path?.description ||
                                      'Подходит на основе твоего текущего профиля.'}
                                  </p>

                                </div>

                              </div>

                              <div className="career-path-match">

                                {Number(
                                  path?.match_percent ?? 0
                                )}
                                % соответствия

                              </div>

                              {requiredSkills.length > 0 && (

                                <div className="career-path-skills">

                                  {requiredSkills.map(
                                    (
                                      skill: string,
                                      skillIndex: number
                                    ) => (

                                      <span
                                        className="tag"
                                        key={skillIndex}
                                      >
                                        {skill}
                                      </span>

                                    )
                                  )}

                                </div>

                              )}

                              {selectedCareerPath === pathId && (

                                <div className="career-path-details">

                                  <div className="career-path-arrow">
                                    ↓
                                  </div>

                                  <strong>
                                    Почему это направление
                                  </strong>

                                  <p>
                                    {path?.why ||
                                      path?.description ||
                                      'Это направление соответствует твоему профилю.'}
                                  </p>

                                  {missingSkills.length > 0 && (

                                    <>
                                      <strong>
                                        Чего не хватает
                                      </strong>

                                      <div className="career-path-skills">

                                        {missingSkills.map(
                                          (
                                            skill: string,
                                            skillIndex: number
                                          ) => (

                                            <span
                                              className="tag"
                                              key={skillIndex}
                                            >
                                              {skill}
                                            </span>

                                          )
                                        )}

                                      </div>
                                    </>

                                  )}

                                  <strong>
                                    Первый шаг
                                  </strong>

                                  <p>
                                    {path?.first_step ||
                                      'Начни изучение ключевых навыков этого направления.'}
                                  </p>

                                  {path?.recommended_project && (

                                    <>
                                      <strong>
                                        Рекомендуемый проект
                                      </strong>

                                      <p>
                                        {path.recommended_project}
                                      </p>
                                    </>

                                  )}

                                  <button
                                    type="button"
                                    className="career-path-button"
                                    onClick={(event) =>
                                      selectCareerPath(
                                        event,
                                        path
                                      )
                                    }
                                  >
                                    Выбрать направление →
                                  </button>

                                </div>

                              )}

                            </div>
                          )
                        }
                      )}

                  </div>

                </div>
              )}

            {/* VACANCIES */}

            {Array.isArray(
              result.vacancies
            ) &&
              result.vacancies.length > 0 && (

                <div className="result-card">

                  <h3>
                    Подходящие вакансии
                  </h3>

                  <div className="vacancies">

                    {result.vacancies.map(
                      (
                        vacancy: any,
                        index: number
                      ) => {

                        const matchPercent =
                          vacancy?.match_percent ?? 0

                        return (

                          <div
                            className="vacancy-card"
                            key={
                              vacancy?.id ||
                              `${vacancy?.title}-${index}`
                            }
                          >

                            <div className="vacancy-header">

                              <div>

                                <h3>
                                  {vacancy?.title}
                                </h3>

                                <p>
                                  {vacancy?.company}
                                </p>

                              </div>

                              <div className="match">
                                {matchPercent}%
                              </div>

                            </div>

                            {Array.isArray(
                              vacancy?.matched_skills
                            ) &&
                              vacancy.matched_skills.length > 0 && (

                                <div className="vacancy-matched">

                                  <span>
                                    Подходят:
                                  </span>

                                  <div className="tags">

                                    {vacancy.matched_skills.map(
                                      (
                                        skill: string,
                                        skillIndex: number
                                      ) => (

                                        <span
                                          className="tag"
                                          key={skillIndex}
                                        >
                                          ✓ {skill}
                                        </span>

                                      )
                                    )}

                                  </div>

                                </div>

                              )}

                            {Array.isArray(
                              vacancy?.missing_skills
                            ) &&
                              vacancy.missing_skills.length > 0 && (

                                <div className="vacancy-missing">

                                  <span>
                                    Не хватает:
                                  </span>

                                  <div className="tags">

                                    {vacancy.missing_skills.map(
                                      (
                                        skill: string,
                                        skillIndex: number
                                      ) => (

                                        <span
                                          className="tag"
                                          key={skillIndex}
                                        >
                                          {skill}
                                        </span>

                                      )
                                    )}

                                  </div>

                                </div>

                              )}

                            {vacancy?.url && (

                              <a
                                href={vacancy.url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                Открыть вакансию →
                              </a>

                            )}

                          </div>
                        )
                      }
                    )}

                  </div>

                </div>
              )}

            {/* ROADMAP */}

            <div className="result-card">

              <h3>
                Карьерный маршрут
              </h3>

              <div className="roadmap">

                {Array.isArray(
                  result.roadmap
                ) &&
                  result.roadmap.map(
                    (
                      step: any,
                      index: number
                    ) => (

                      <div
                        className="roadmap-step"
                        key={
                          step?.step ??
                          index
                        }
                      >

                        <div className="step-number">
                          {step?.step ??
                            index + 1}
                        </div>

                        <div>

                          <h4>
                            {step?.title}
                          </h4>

                          <p>
                            {step?.description}
                          </p>

                        </div>

                      </div>

                    )
                  )}

              </div>

            </div>

            {/* NEXT STEP */}

            <div className="result-card next-step">

              <h3>
                Следующий шаг
              </h3>

              <p>
                {result.next_step ||
                  'Начни с изучения ключевых навыков выбранного направления.'}
              </p>

            </div>

            {/* HISTORY */}

            {history.length > 0 && (

              <div className="result-card">

                <span className="result-label">
                  ИСТОРИЯ АНАЛИЗОВ
                </span>

                <h3>
                  Твоя динамика
                </h3>

                <div className="history-list">

                  {history.map(
                    (item) => (

                      <div
                        className="history-item"
                        key={item.id}
                      >

                        <div className="history-info">

                          <strong>
                            {item.target_role}
                          </strong>

                          <span>
                            Анализ #{item.id}
                          </span>

                        </div>

                        <div className="history-match">
                          {item.career_match_percent}%
                        </div>

                      </div>

                    )
                  )}

                </div>

              </div>
            )}

          </section>
        )}

      </main>

    </div>
  )
}

export default App
