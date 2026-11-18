import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Modal } from './Modal'

describe('Modal', () => {
  it('renderiza o footer fora do container com scroll do corpo', () => {
    render(
      <Modal title="Título" onClose={vi.fn()} footer={<button type="button">Fechar</button>}>
        <p>Conteúdo do corpo</p>
      </Modal>,
    )

    // A "X" do cabeçalho também tem aria-label "Fechar" — o botão do rodapé é
    // o que tem o texto visível "Fechar".
    const footerButton = screen.getAllByRole('button', { name: 'Fechar' }).find((button) => button.textContent === 'Fechar')
    expect(footerButton).toBeDefined()
    const scrollArea = screen.getByText('Conteúdo do corpo').closest('.overflow-y-auto')
    expect(scrollArea).not.toBeNull()
    expect(scrollArea?.contains(footerButton as HTMLElement)).toBe(false)
  })

  it('funciona normalmente sem footer (compatibilidade com os outros modais)', () => {
    render(
      <Modal title="Título" onClose={vi.fn()}>
        <p>Conteúdo do corpo</p>
      </Modal>,
    )

    expect(screen.getByText('Conteúdo do corpo')).toBeInTheDocument()
  })
})
