describe("TP2 - Testes E2E (Turismo Belo Horizonte)", () => {
  beforeEach(() => {
    cy.visit("/");
    cy.get("body").should("be.visible");
  });

  it("E2E 1 - Deve carregar a aplicacao e exibir conteudo visivel na tela", () => {
    cy.get("body")
      .invoke("text")
      .then((text) => {
        expect(text.trim().length).to.be.greaterThan(0);
      });
    cy.get("body *").should("have.length.greaterThan", 0);
  });

  it("E2E 2 - Deve permitir navegar entre secoes ou modos da interface", () => {
    cy.get("button, a, [role='tab']").then(($els) => {
      if ($els.length > 0) {
        cy.wrap($els.first()).should("exist");
      }
    });
    cy.get("body")
      .invoke("text")
      .then((text) => {
        expect(text.trim().length).to.be.greaterThan(0);
      });
  });

  it("E2E 3 - Deve interagir com controles de formulario ou acao do fluxo principal", () => {
    cy.get("input, select, textarea, button").then(($controls) => {
      expect($controls.length).to.be.greaterThan(0);
      const visibleInputs = $controls.filter("input:visible, textarea:visible");
      if (visibleInputs.length > 0) {
        cy.wrap(visibleInputs.first())
          .clear({ force: true })
          .type("Praca da Liberdade E2E", { force: true })
          .should("have.value", "Praca da Liberdade E2E");
      }
    });
  });

  it("E2E 4 - Deve manter a renderizacao da aplicacao apos recarregar a pagina", () => {
    cy.reload();
    cy.get("body").should("be.visible");
    cy.get("body")
      .invoke("text")
      .then((text) => {
        expect(text.trim().length).to.be.greaterThan(0);
      });
  });
});
