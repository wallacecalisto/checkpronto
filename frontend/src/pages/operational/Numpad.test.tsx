import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Numpad } from './Numpad'

describe('Numpad', () => {
  it('chama onChange com o dígito pressionado acrescentado ao valor atual', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<Numpad value="12" maxLength={4} onChange={onChange} />)

    await user.click(screen.getByRole('button', { name: '3' }))

    expect(onChange).toHaveBeenCalledWith('123')
  })

  it('apaga o último dígito ao clicar em "Apagar"', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<Numpad value="123" maxLength={4} onChange={onChange} />)

    await user.click(screen.getByRole('button', { name: 'Apagar' }))

    expect(onChange).toHaveBeenCalledWith('12')
  })

  it('não deixa passar do maxLength', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<Numpad value="1234" maxLength={4} onChange={onChange} />)

    await user.click(screen.getByRole('button', { name: '5' }))

    expect(onChange).not.toHaveBeenCalled()
  })

  it('não responde a cliques quando disabled', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<Numpad value="" maxLength={4} onChange={onChange} disabled />)

    await user.click(screen.getByRole('button', { name: '1' }))

    expect(onChange).not.toHaveBeenCalled()
  })
})
