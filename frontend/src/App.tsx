import { useState } from 'react'
import './App.css'

const API_BASE_URL =
  import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [goal, setGoal] = useState('')
  const [skills, setSkills] = useState('')
  const [experience, setExperience] = useState('')
  const [skillLevels, setSkillLevels] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  const skillList = skills
    .split(',')
    .map((skill) => skill.trim())
    .filter((skill) => skill.length > 0)

  // =========================
  // AI ANALYSIS
  // =========================

  const analyzeCareer = async () => {
    if (!goal.trim()) {
      alert('Укажи желаемую профессию')
      return
    }

    setLoading(true)
    setResult(null)

    try {
      // =========================
      // CREATE USER
      // =========================

      const userResponse = await fetch(`${API_BASE_URL}/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: 'Danya',
          email: `danya_${Date.now()}@test.com`,
          resume: experience,
          goal: goal,
        }),
      })

      if (!userResponse.ok) {
        const errorText = await userResponse.text()

        throw new Error(
          `Ошибка создания пользователя: ${userResponse.status} ${errorText}`,
        )
      }

      const user = await userResponse.json()

      console.log('USER CREATED:', user)

      // =========================
      // SAVE SKILLS
      // =========================

      for (const skill of skillList) {
        const skillResponse = await fetch(`${API_BASE_URL}/skills`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: user.user_id,
            skill: skill,
            level: skillLevels[skill] || 3,
          }),
        })

        if (!skillResponse.ok) {
          const errorText = await skillResponse.text()

          throw new Error(
            `Ошибка сохранения навыка "${skill}": ${skillResponse.status} ${errorText}`,
          )
        }
      }

      // =========================
      // SAVE PROFILE
      // =========================

      const profileResponse = await fetch(`${API_BASE_URL}/profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.user_id,
          skills: skillList,
          experience: experience,
          projects: experience.trim() ? [experience.trim()] : [],
        }),
      })

      if (!profileResponse.ok) {
        const errorText = await profileResponse.text()

        throw new Error(
          `Ошибка сохранения профиля: ${profileResponse.status} ${errorText}`,
        )
      }

      // =========================
      // AI ANALYSIS
      // =========================

      const response = await fetch(
        `${API_BASE_URL}/analyze?user_id=${user.user_id}`,
        {
          method: 'POST',
        },
      )

      if (!response.ok) {
        const errorText = await response.text()

        throw new Error(
          `Ошибка AI-анализа: ${response.status} ${errorText}`,
        )
      }

      const data = await response.json()

      console.log('AI RESULT:', data)

      setResult(data)

      // =========================
      // SCROLL TO RESULT
      // =========================

      setTimeout(() => {
        document.querySelector('.result')?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        })
      }, 100)
    } catch (error) {
      console.error('ОШИБКА:', error)

      if (error instanceof TypeError) {
        alert(
          `Frontend не может подключиться к Backend. Проверь адрес: ${API_BASE_URL}`,
        )
      } else {
        alert(
          error instanceof Error
            ? error.message
            : 'Произошла неизвестная ошибка',
        )
      }
    } finally {
      setLoading(false)
    }
  }

  // =========================
  // CAREER MATCH
  // =========================

  const calculateCareerMatch = () => {
    if (!result) {
      return 0
    }

    // Если Backend прислал готовый процент
    if (typeof result.career_match_percent === 'number') {
      return Math.round(
        Math.max(
          0,
          Math.min(100, result.career_match_percent),
        ),
      )
    }

    // Если missing_skills отсутствует
    const missingSkills = result.missing_skills || []

    if (missingSkills.length === 0) {
      return 100
    }

    let totalProgress = 0

    for (const item of missingSkills) {
      const currentLevel = Number(item.current_level ?? 0)
      const requiredLevel = Number(item.required_level ?? 5)

      if (requiredLevel > 0) {
        totalProgress += Math.min(
          100,
          (currentLevel / requiredLevel) * 100,
        )
      }
    }

    return Math.round(
      Math.max(
        0,
        Math.min(
          100,
          totalProgress / missingSkills.length,
        ),
      ),
    )
  }

  const careerMatch = calculateCareerMatch()

  // =========================
  // RENDER
  // =========================

  return (
    <div className="app">

      {/* =========================
          HEADER
      ========================= */}

      <header className="header">
        <div className="logo">
          AI Career Navigator
        </div>

        <div className="subtitle">
          Твой персональный навигатор в карьере
        </div>
      </header>

      {/* =========================
          MAIN
      ========================= */}

      <main className="container">

        {/* =========================
            HERO
        ========================= */}

        <section className="hero">

          <div className="hero-badge">
            AI • CAREER • NAVIGATION
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

        {/* =========================
            PROFILE FORM
        ========================= */}

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

          {/* GOAL */}

          <label>
            Желаемая профессия
          </label>

          <input
            type="text"
            placeholder="Например: Backend Developer"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
          />

          {/* SKILLS */}

          <label>
            Текущие навыки
          </label>

          <textarea
            placeholder="Например: Python, C++, Git, SQL"
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
          />

          {/* SKILL LEVELS */}

          {skillList.length > 0 && (

            <div className="skill-levels">

              <label>
                Уровень навыков
              </label>

              {skillList.map((skill) => (

                <div
                  className="skill-level-row"
                  key={skill}
                >

                  <strong>
                    {skill}
                  </strong>

                  <select
                    value={skillLevels[skill] || 3}
                    onChange={(e) =>
                      setSkillLevels({
                        ...skillLevels,
                        [skill]: Number(e.target.value),
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

              ))}

            </div>

          )}

          {/* EXPERIENCE */}

          <label>
            Опыт и проекты
          </label>

          <textarea
            placeholder="Расскажи о своём опыте, проектах и обучении"
            value={experience}
            onChange={(e) => setExperience(e.target.value)}
          />

          {/* BUTTON */}

          <button
            onClick={analyzeCareer}
            disabled={loading || !goal.trim()}
          >
            {loading
              ? 'Анализируем...'
              : 'Построить карьерный маршрут →'}
          </button>

        </section>

        {/* =========================
            RESULT
        ========================= */}

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
                  Анализ профиля, навыков и требований
                  целевой профессии.
                </p>

              </div>

            </div>

            {/* =========================
                TARGET + LEVEL
            ========================= */}

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

            {/* =========================
                STRENGTHS
            ========================= */}

            <div className="result-card">

              <h3>
                Сильные стороны
              </h3>

              <ul className="result-list">

                {result.strengths?.map(
                  (
                    item: any,
                    index: number,
                  ) => (

                    <li key={index}>

                      {typeof item === 'object'
                        ? `${item.skill}: уровень ${item.level}`
                        : item}

                    </li>

                  ),
                )}

              </ul>

            </div>

            {/* =========================
                MISSING SKILLS
            ========================= */}

            <div className="result-card">

              <h3>
                Что нужно изучить
              </h3>

              <div className="skills-list">

                {result.missing_skills?.map(
                  (
                    item: any,
                    index: number,
                  ) => {

                    const currentLevel =
                      Number(item.current_level ?? 0)

                    const requiredLevel =
                      Number(item.required_level ?? 5)

                    const progress =
                      requiredLevel > 0
                        ? Math.min(
                            100,
                            (currentLevel / requiredLevel) * 100,
                          )
                        : 0

                    return (

                      <div
                        className="skill-item"
                        key={index}
                      >

                        <div className="skill-header">

                          <strong>
                            {item.skill}
                          </strong>

                          <span>
                            {currentLevel} / {requiredLevel}
                          </span>

                        </div>

                        <div className="progress">

                          <div
                            className="progress-bar"
                            style={{
                              width: `${progress}%`,
                            }}
                          />

                        </div>

                        <p>
                          {item.reason}
                        </p>

                      </div>

                    )
                  },
                )}

              </div>

            </div>

            {/* =========================
                RECOMMENDED PROJECT
            ========================= */}

            <div className="result-card">

              <h3>
                Рекомендуемый проект
              </h3>

              <p>
                {typeof result.recommended_project === 'string'
                  ? result.recommended_project
                  : result.recommended_project?.description ||
                    result.recommended_project?.name ||
                    'Проект пока не сформирован.'}
              </p>

              {result.recommended_project?.technologies && (

                <div className="tags">

                  {result.recommended_project.technologies.map(
                    (
                      technology: string,
                      index: number,
                    ) => (

                      <span key={index}>
                        {technology}
                      </span>

                    ),
                  )}

                </div>

              )}

            </div>

            {/* =========================
                CAREER MATCH
            ========================= */}

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
                    width: `${careerMatch}%`,
                  }}
                />

              </div>

              <p>
                Показатель отражает соответствие
                текущих навыков требованиям выбранной
                профессии.
              </p>

            </div>

            {/* =========================
                VACANCIES
            ========================= */}

            {result.vacancies?.length > 0 && (

              <div className="result-card">

                <h3>
                  Подходящие вакансии
                </h3>

                <div className="vacancies">

                  {result.vacancies.map(
                    (
                      vacancy: any,
                      index: number,
                    ) => {

                      const matchPercent =
                        vacancy.match_percent ?? 0

                      return (

                        <div
                          className="vacancy-card"
                          key={
                            vacancy.id ||
                            `${vacancy.title}-${index}`
                          }
                        >

                          <div className="vacancy-header">

                            <div>

                              <h3>
                                {vacancy.title}
                              </h3>

                              <p>
                                {vacancy.company}
                              </p>

                            </div>

                            <div className="match">
                              {matchPercent}%
                            </div>

                          </div>

                          {/* MATCHED SKILLS */}

                          {vacancy.matched_skills?.length > 0 && (

                            <div className="vacancy-matched">

                              <span>
                                Подходят:
                              </span>

                              <div className="tags">

                                {vacancy.matched_skills.map(
                                  (
                                    skill: string,
                                    skillIndex: number,
                                  ) => (

                                    <span
                                      className="tag"
                                      key={skillIndex}
                                    >
                                      ✓ {skill}
                                    </span>

                                  ),
                                )}

                              </div>

                            </div>

                          )}

                          {/* MISSING SKILLS */}

                          {vacancy.missing_skills?.length > 0 && (

                            <div className="vacancy-missing">

                              <span>
                                Не хватает:
                              </span>

                              <div className="tags">

                                {vacancy.missing_skills.map(
                                  (
                                    skill: string,
                                    skillIndex: number,
                                  ) => (

                                    <span
                                      className="tag"
                                      key={skillIndex}
                                    >
                                      {skill}
                                    </span>

                                  ),
                                )}

                              </div>

                            </div>

                          )}

                        </div>

                      )
                    },
                  )}

                </div>

              </div>

            )}

            {/* =========================
                ROADMAP
            ========================= */}

            <div className="result-card">

              <h3>
                Карьерный маршрут
              </h3>

              <div className="roadmap">

                {result.roadmap?.map(
                  (step: any) => (

                    <div
                      className="roadmap-step"
                      key={step.step}
                    >

                      <div className="step-number">
                        {step.step}
                      </div>

                      <div>

                        <h4>
                          {step.title}
                        </h4>

                        <p>
                          {step.description}
                        </p>

                      </div>

                    </div>

                  ),
                )}

              </div>

            </div>

            {/* =========================
                NEXT STEP
            ========================= */}

            <div className="result-card next-step">

              <h3>
                Следующий шаг
              </h3>

              <p>
                {result.next_step ||
                  'Начни с изучения SQL и PostgreSQL, затем переходи к FastAPI.'}
              </p>

            </div>

          </section>

        )}

      </main>

    </div>
  )
}

export default App